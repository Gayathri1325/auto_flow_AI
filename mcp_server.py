# mcp_server.py
from fastmcp import FastMCP

mcp = FastMCP(name="AutoFlowConnectors")

@mcp.tool
def summarize_text(content: str) -> str:
    """Summarizes or formats data for external reporting."""
    return f"PROCESSED SUMMARY:\n{content.strip()}"

@mcp.tool
def send_notification_email(recipient: str, subject: str, body: str) -> str:
    """Sends an email update. (Simulated execution for safety demo)"""
    return f"Email successfully dispatched to {recipient} with subject: '{subject}'"

if __name__ == "__main__":
    mcp.run()