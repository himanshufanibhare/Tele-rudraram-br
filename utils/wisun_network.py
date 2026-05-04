"""
WiSUN Network Management Class
Handles network status and node connectivity
"""

import re
from utils.helpers import shell_command
from config.nodes import known_ips


class WisunNetwork:
    """
    Manages WiSUN network operations and node status
    """
    
    def __init__(self):
        pass
    
    def load_nodes(self):
        """
        Load all known node IP addresses
        
        Returns:
            dict: Dictionary of known node names and IPs
        """
        try:
            return known_ips
        except Exception as e:
            print(f"Error loading nodes: {e}")
            return {}
    
    def get_wisun_status(self):
        """
        Get current WiSUN network status from border router
        
        Returns:
            tuple: (node_list: list, node_count: int)
        """
        node_list_output = shell_command("wsbrd_cli status")
        # Match IPv6 addresses in format fd12:xxxx:...
        ip_pattern = r"fd12:[a-f0-9:]+(?:\s|$)"
        ip_addresses = re.findall(ip_pattern, node_list_output)
        
        # Clean up matched IPs (remove trailing whitespace)
        nodes = [ip.strip() for ip in ip_addresses]
        
        return nodes, len(nodes)
    
    def get_connected_nodes(self):
        """
        Get lists of connected and disconnected nodes
        
        Returns:
            tuple: (connected_nodes: list, disconnected_nodes: list, summary: str)
        """
        # Get IPs from wisun status
        active_nodes, node_count = self.get_wisun_status()
        known_nodes_dict = self.load_nodes()
        known_nodes_list = list(known_nodes_dict.values())
        
        connected = []
        disconnected = []
        
        # Check each known node
        for node_name, ip in known_nodes_dict.items():
            if ip in active_nodes:
                connected.append((node_name, ip))
            else:
                disconnected.append((node_name, ip))
        
        # Build summary string
        summary = f"Total Nodes: {len(known_nodes_list)}\nConnected: {len(connected)}\nDisconnected: {len(disconnected)}"
        
        return connected, disconnected, summary
    
    def format_node_report(self):
        """
        Format a comprehensive node report
        
        Returns:
            str: Formatted report of connected/disconnected nodes
        """
        connected, disconnected, summary = self.get_connected_nodes()
        
        report = f"<b>WiSUN Network Status</b>\n\n{summary}\n\n"
        
        if connected:
            report += "<b>Connected Nodes:</b>\n"
            for node_name, ip in connected:
                report += f"✅ {node_name}: {ip}\n"
        else:
            report += "<b>Connected Nodes:</b>\nNone\n"
        
        report += "\n"
        
        if disconnected:
            report += "<b>Disconnected Nodes:</b>\n"
            for node_name, ip in disconnected:
                report += f"❌ {node_name}: {ip}\n"
        else:
            report += "<b>Disconnected Nodes:</b>\nNone\n"
        
        return report
    
    def format_connected_nodes(self):
        """
        Format report of only connected nodes
        
        Returns:
            str: Formatted report of connected nodes with count
        """
        connected, _, _ = self.get_connected_nodes()
        
        report = f"<b>Connected Nodes: {len(connected)}</b>\n\n"
        
        if connected:
            for node_name, ip in connected:
                report += f"✅ {node_name}: {ip}\n"
        else:
            report += "No connected nodes.\n"
        
        return report
    
    def format_disconnected_nodes(self):
        """
        Format report of only disconnected nodes
        
        Returns:
            str: Formatted report of disconnected nodes with count
        """
        _, disconnected, _ = self.get_connected_nodes()
        
        report = f"<b>Disconnected Nodes: {len(disconnected)}</b>\n\n"
        
        if disconnected:
            for node_name, ip in disconnected:
                report += f"❌ {node_name}: {ip}\n"
        else:
            report += "All nodes are connected.\n"
        
        return report
