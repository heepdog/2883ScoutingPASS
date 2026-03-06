import http.server
import ssl

server_address = ('', 4443)  # Use port 4443 or another available port
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

# Wrap the socket with SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
try:
    # Load your certificate and key files
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem") 
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    print(f"Serving HTTPS on port {server_address[1]}...")
    httpd.serve_forever()
except FileNotFoundError:
    print("Certificate (cert.pem) or key (key.pem) file not found.")
    print("Please ensure your certificate and key files are in the script directory.")
except Exception as e:
    print(f"An error occurred: {e}")
