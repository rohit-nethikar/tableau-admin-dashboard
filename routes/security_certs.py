from datetime import datetime, timezone
from urllib.parse import urlparse
import ssl
import socket
import json
import urllib.request
import urllib.error

from flask import Blueprint, render_template, request, redirect, url_for, flash

import db
from auth import login_required
from config import settings
import tableau_client
import crypto

bp = Blueprint("security_certs", __name__)


def get_certificate_details(hostname, port=443):
    """Fetch SSL certificate details from a hostname."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                # Convert dates from ASN1 format to datetime
                not_before = ssl.cert_time_to_seconds(cert['notBefore'])
                not_after = ssl.cert_time_to_seconds(cert['notAfter'])

                not_before_dt = datetime.fromtimestamp(not_before, tz=timezone.utc)
                not_after_dt = datetime.fromtimestamp(not_after, tz=timezone.utc)

                # Days until expiration
                days_remaining = (not_after_dt - datetime.now(timezone.utc)).days

                # Extract subject and issuer info
                subject = {item[0][0]: item[0][1] for item in cert.get('subject', [])}
                issuer = {item[0][0]: item[0][1] for item in cert.get('issuer', [])}

                # Extract SANs (Subject Alternative Names)
                san_list = []
                for ext in cert.get('subjectAltName', []):
                    if ext[0] == 'DNS':
                        san_list.append(ext[1])

                return {
                    'success': True,
                    'subject_cn': subject.get('commonName', 'N/A'),
                    'subject_org': subject.get('organizationName', 'N/A'),
                    'subject_country': subject.get('countryName', 'N/A'),
                    'issuer_cn': issuer.get('commonName', 'N/A'),
                    'issuer_org': issuer.get('organizationName', 'N/A'),
                    'not_before': not_before_dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'not_after': not_after_dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'days_remaining': days_remaining,
                    'serial_number': cert.get('serialNumber', 'N/A'),
                    'version': cert.get('version', 'N/A'),
                    'san_list': san_list,
                    'status': 'expired' if days_remaining < 0 else ('warning' if days_remaining < 30 else 'valid'),
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_node_info_from_sessions_api(auth_token, server_url, api_version):
    """Try to infer node info from active sessions (workaround if direct nodes endpoint unavailable)."""
    try:
        url = f"{server_url}/api/{api_version}/sites/0/sessions"
        request = urllib.request.Request(
            url,
            headers={'X-Tableau-Auth': auth_token, 'Accept': 'application/json'},
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode('utf-8'))

            # Extract unique server/node info from sessions if available
            sessions = payload.get('session', [])
            if isinstance(sessions, dict):
                sessions = [sessions]

            # Parse session data for node information
            nodes_found = {}
            for session in sessions:
                if isinstance(session, dict) and 'serverAddress' in session:
                    addr = session.get('serverAddress', 'Unknown')
                    if addr not in nodes_found:
                        nodes_found[addr] = {
                            'name': addr,
                            'ip': addr,
                            'status': 'Active'
                        }

            return list(nodes_found.values()) if nodes_found else []

    except Exception:
        pass

    return []


def get_server_nodes_via_admin_api(auth_token, server_url, api_version, site_id):
    """Try to fetch node info via Tableau's administrative GraphQL or REST endpoints."""
    try:
        # Try GraphQL metadata API first for node information
        graphql_query = """
        {
          servers {
            name
            addresses {
              address
              ipAddress
            }
          }
        }
        """

        url = f"{server_url}/api/metadata/graphql"
        headers = {
            "X-Tableau-Auth": auth_token,
            "Content-Type": "application/json",
        }

        try:
            request = urllib.request.Request(
                url,
                data=json.dumps({"query": graphql_query}).encode('utf-8'),
                headers=headers,
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
                if 'data' in payload and 'servers' in payload['data']:
                    servers = payload['data']['servers']
                    if servers:
                        node_list = []
                        for server_item in servers:
                            addresses = server_item.get('addresses', [])
                            for addr in addresses:
                                node_list.append({
                                    'name': server_item.get('name', 'N/A'),
                                    'ip': addr.get('ipAddress') or addr.get('address', 'N/A'),
                                    'status': 'Active',  # If returned by API, it's active
                                })
                        if node_list:
                            return node_list
        except Exception:
            pass

    except Exception:
        pass

    return []


def get_server_nodes():
    """Fetch backend server node information from Tableau REST API."""
    try:
        # Get credentials from db
        pat_name = db.get_config('pat_name')
        pat_encrypted = db.get_config('pat_encrypted')

        if not pat_name or not pat_encrypted:
            return {
                'success': False,
                'error': 'No credentials configured',
                'nodes': []
            }

        # Decrypt the PAT secret
        try:
            pat_secret = crypto.decrypt_value(pat_encrypted)
        except Exception:
            return {
                'success': False,
                'error': 'Could not decrypt credentials',
                'nodes': []
            }

        # Create an authenticated connection
        with tableau_client.signed_in_server(
            settings.server_url,
            settings.default_site,
            pat_name,
            pat_secret
        ) as server:
            # Try multiple API versions and endpoints
            api_versions = [server.version, "3.21", "3.20", "3.19", "3.18", "3.17", "3.16"]
            endpoints_to_try = []

            for api_ver in api_versions:
                endpoints_to_try.extend([
                    f"{settings.server_url}/api/{api_ver}/sites/{server.site_id}/server/info",
                    f"{settings.server_url}/api/{api_ver}/server/info",
                    f"{settings.server_url}/api/{api_ver}/server/nodes",
                    f"{settings.server_url}/api/{api_ver}/servers",
                ])

            node_list = []
            last_error = None

            for endpoint_url in endpoints_to_try:
                try:
                    request = urllib.request.Request(
                        endpoint_url,
                        headers={'X-Tableau-Auth': server.auth_token, 'Accept': 'application/json'},
                    )

                    with urllib.request.urlopen(request, timeout=10) as response:
                        payload = json.loads(response.read().decode('utf-8'))

                        # Try different payload structures based on endpoint
                        nodes = None

                        # Check various possible locations for node data
                        if 'nodes' in payload:
                            nodes = payload.get('nodes', {})
                        elif 'node' in payload:
                            nodes = payload.get('node', {})
                        elif 'serverinfo' in payload:
                            server_info = payload.get('serverinfo', {})
                            if 'nodes' in server_info:
                                nodes = server_info.get('nodes', {})

                        # Handle node structure
                        if nodes:
                            # Could be a dict with 'node' key or direct list
                            if isinstance(nodes, dict):
                                if 'node' in nodes:
                                    node_data = nodes['node']
                                else:
                                    node_data = nodes
                            else:
                                node_data = nodes

                            # Normalize to list
                            if isinstance(node_data, dict):
                                node_data = [node_data]
                            elif not isinstance(node_data, list):
                                node_data = []

                            for node in node_data:
                                if isinstance(node, dict):
                                    node_list.append({
                                        'name': node.get('name') or node.get('@name', 'N/A'),
                                        'ip': node.get('ip') or node.get('@ip', 'N/A'),
                                        'status': node.get('status') or node.get('@status', 'Unknown'),
                                    })

                        if node_list:
                            break

                except urllib.error.HTTPError as http_err:
                    last_error = f"HTTP {http_err.code}"
                    continue
                except Exception as e:
                    last_error = str(e)
                    continue

            # If REST API didn't work, try GraphQL metadata API
            if not node_list:
                node_list = get_server_nodes_via_admin_api(
                    server.auth_token,
                    settings.server_url,
                    server.version,
                    server.site_id
                )

            # Last resort: try sessions API to infer nodes
            if not node_list:
                node_list = get_node_info_from_sessions_api(
                    server.auth_token,
                    settings.server_url,
                    server.version
                )

            if node_list:
                return {
                    'success': True,
                    'nodes': node_list,
                    'node_count': len(node_list)
                }
            else:
                # Return success but with message that we couldn't find node details
                # But we can confirm admin access is working
                return {
                    'success': False,
                    'error': f'Node information endpoint not found in this Tableau version. Your admin PAT is working correctly though! Last error: {last_error or "API endpoint not available"}. Node details may require direct database access or TSM (Tableau Server Manager) configuration.',
                    'nodes': [],
                    'admin_confirmed': True
                }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'nodes': []
        }


def get_stored_nodes():
    """Retrieve manually added backend nodes from database."""
    nodes_json = db.get_config('backend_nodes')
    if nodes_json:
        try:
            return json.loads(nodes_json)
        except json.JSONDecodeError:
            return []
    return []


def store_node(node_name, node_ip, node_status):
    """Store a backend node in the database."""
    nodes = get_stored_nodes()
    for node in nodes:
        if node['name'].lower() == node_name.lower():
            node['name'] = node_name
            node['ip'] = node_ip
            node['status'] = node_status
            db.set_config('backend_nodes', json.dumps(nodes))
            return True
    nodes.append({
        'name': node_name,
        'ip': node_ip,
        'status': node_status
    })
    db.set_config('backend_nodes', json.dumps(nodes))
    return True


def delete_node(node_name):
    """Delete a backend node from the database."""
    nodes = get_stored_nodes()
    nodes = [n for n in nodes if n['name'].lower() != node_name.lower()]
    db.set_config('backend_nodes', json.dumps(nodes))
    return True


@bp.route("/security-certs/node/add", methods=["POST"])
@login_required
def add_node():
    """Add a backend node."""
    node_name = request.form.get('node_name', '').strip()
    node_ip = request.form.get('node_ip', '').strip()
    node_status = request.form.get('node_status', '').strip()

    if not node_name or not node_ip or not node_status:
        flash("Node name, IP, and status are all required.", "error")
        return redirect(url_for('security_certs.list_security_certs'))

    try:
        store_node(node_name, node_ip, node_status)
        flash(f"Node '{node_name}' added successfully!", "success")
    except Exception as e:
        flash(f"Error adding node: {e}", "error")

    return redirect(url_for('security_certs.list_security_certs'))


@bp.route("/security-certs/node/delete/<node_name>", methods=["POST"])
@login_required
def delete_node_route(node_name):
    """Delete a backend node."""
    try:
        delete_node(node_name)
        flash(f"Node '{node_name}' deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting node: {e}", "error")

    return redirect(url_for('security_certs.list_security_certs'))


@bp.route("/security-certs")
@login_required
def list_security_certs():
    # Parse the Tableau server URL to get hostname
    parsed_url = urlparse(settings.server_url)
    hostname = parsed_url.hostname or 'localhost'
    port = parsed_url.port or 443

    # Fetch certificate details
    cert_info = get_certificate_details(hostname, port)

    # Fetch Tableau server info
    server_info = db.fetch_server_info()

    # Fetch server node information
    nodes_info = get_server_nodes()

    # Get manually stored nodes
    stored_nodes = get_stored_nodes()

    return render_template(
        "security_certs.html",
        cert_info=cert_info,
        server_info=server_info,
        nodes_info=nodes_info,
        stored_nodes=stored_nodes,
        server_url=settings.server_url,
        hostname=hostname,
        port=port,
        last_refresh=db.latest_refresh(None),
    )
