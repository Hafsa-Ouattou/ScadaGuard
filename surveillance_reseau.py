
import psutil

PORTS_COURANTS = {80, 443, 53, 22, 21, 25, 143, 993, 995, 3306, 5432, 8080}


def obtenir_connexions_actives():
    
    connexions = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_ESTABLISHED and conn.raddr:
                port_distant = conn.raddr.port
                connexions.append({
                    "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                    "distant": f"{conn.raddr.ip}:{port_distant}",
                    "pid": conn.pid if conn.pid else "N/A",
                    "suspect": port_distant not in PORTS_COURANTS,
                })
    except (psutil.AccessDenied, PermissionError):
        
        pass
    return connexions
