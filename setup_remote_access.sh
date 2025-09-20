#!/bin/bash

# Setup script for remote UI access to Langflow on VM

echo "🌐 Setting up Remote Access for Langflow UI"
echo "========================================="

# Option 1: Install and configure Langflow for remote access
install_langflow() {
    echo "📦 Installing Langflow..."
    pip install langflow>=1.0.0 langfuse langsmith

    # Create systemd service for persistent running
    sudo tee /etc/systemd/system/langflow.service > /dev/null << 'EOF'
[Unit]
Description=Langflow Visual Pipeline Studio
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/AIT
Environment="PATH=/home/$USER/.local/bin:/usr/bin"
ExecStart=/home/$USER/.local/bin/langflow run --host 0.0.0.0 --port 7860
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable langflow
    echo "✅ Langflow installed as service"
}

# Option 2: Setup ngrok for public access
setup_ngrok() {
    echo "🔗 Setting up ngrok..."

    # Check if ngrok is installed
    if ! command -v ngrok &> /dev/null; then
        wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
        tar xzf ngrok-v3-stable-linux-amd64.tgz
        sudo mv ngrok /usr/local/bin/
        rm ngrok-v3-stable-linux-amd64.tgz
    fi

    echo "✅ ngrok installed"
    echo "Run: ngrok http 7860"
}

# Option 3: Setup Tailscale for secure access
setup_tailscale() {
    echo "🔐 Setting up Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "✅ Tailscale installed"
    echo "Run: sudo tailscale up"
}

# Option 4: Configure firewall for direct access (GCP)
setup_gcp_firewall() {
    echo "🔥 Configuring GCP firewall..."

    # Get instance name and zone
    INSTANCE=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/name" -H "Metadata-Flavor: Google")
    ZONE=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/zone" -H "Metadata-Flavor: Google" | cut -d'/' -f4)

    echo "Instance: $INSTANCE"
    echo "Zone: $ZONE"

    # Create firewall rule
    gcloud compute firewall-rules create langflow-ui \
        --allow tcp:7860 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow Langflow UI access"

    # Add network tag to instance
    gcloud compute instances add-tags $INSTANCE \
        --tags langflow-ui \
        --zone $ZONE

    # Get external IP
    EXTERNAL_IP=$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google")

    echo "✅ Firewall configured"
    echo "Access at: http://$EXTERNAL_IP:7860"
}

# Menu
echo ""
echo "Choose setup method:"
echo "1) SSH Port Forwarding (recommended - most secure)"
echo "2) ngrok (easy public access)"
echo "3) Tailscale (VPN access)"
echo "4) Direct GCP Firewall (if on GCP)"
echo "5) Install all options"
echo ""
read -p "Choice (1-5): " choice

case $choice in
    1)
        install_langflow
        echo ""
        echo "✅ Setup complete! Now:"
        echo "1. Exit SSH"
        echo "2. Reconnect with: ssh -L 7860:localhost:7860 $USER@$(hostname -I | awk '{print $1}')"
        echo "3. Start Langflow: sudo systemctl start langflow"
        echo "4. Access at: http://localhost:7860"
        ;;
    2)
        install_langflow
        setup_ngrok
        echo ""
        echo "✅ Setup complete! Now:"
        echo "1. Start Langflow: langflow run --host 0.0.0.0 --port 7860"
        echo "2. In new terminal: ngrok http 7860"
        echo "3. Access via ngrok URL"
        ;;
    3)
        install_langflow
        setup_tailscale
        echo ""
        echo "✅ Setup complete! Now:"
        echo "1. Authenticate: sudo tailscale up"
        echo "2. Start Langflow: sudo systemctl start langflow"
        echo "3. Get IP: tailscale ip -4"
        echo "4. Access at: http://[tailscale-ip]:7860"
        ;;
    4)
        install_langflow
        setup_gcp_firewall
        echo ""
        echo "✅ Setup complete! Now:"
        echo "1. Start Langflow: sudo systemctl start langflow"
        echo "2. Access at URL shown above"
        ;;
    5)
        install_langflow
        setup_ngrok
        setup_tailscale
        setup_gcp_firewall
        echo ""
        echo "✅ All options installed!"
        ;;
esac

echo ""
echo "📝 Quick Commands:"
echo "Start Langflow: sudo systemctl start langflow"
echo "Stop Langflow: sudo systemctl stop langflow"
echo "View logs: sudo journalctl -u langflow -f"