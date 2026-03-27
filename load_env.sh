#!/bin/bash
#
# Load API environment variables for ComfyUI-API-DockerCPU
#
# Usage:
#   source load_env.sh              # Load environment variables
#   ./load_env.sh                  # Or run directly (variables won't persist)
#
# This script loads environment variables from the API configuration file.
#

# set -e

# Path to the environment file
ENV_FILE="/opt/docker-homeweb/apps/COMFYUI_API.env"

# Check if the env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file not found: $ENV_FILE"
    echo "Please ensure the file exists or update ENV_FILE in this script."
    exit 1
fi

# Function to export variables from .env file
load_env_file() {
    local env_file="$1"
    
    if [ ! -f "$env_file" ]; then
        echo "Error: File not found: $env_file"
        return 1
    fi
    
    # Read each line and export it
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip empty lines and comments
        if [ -z "$key" ] || [[ "$key" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Trim whitespace from key
        key=$(echo "$key" | xargs)
        
        # Export the variable
        export "$key=$value"
        echo "Loaded: $key"
    done < "$env_file"
}

echo "Loading environment variables from: $ENV_FILE"
echo "============================================"

# Load the environment file
load_env_file "$ENV_FILE"

echo ""
echo "============================================"
echo "Environment variables loaded successfully!"
echo ""
echo "Available API keys:"
[ -n "$REPLICATE_API_TOKEN" ] && echo "  ✓ REPLICATE_API_TOKEN"
[ -n "$FAL_KEY" ] && echo "  ✓ FAL_KEY"
[ -n "$HF_TOKEN" ] && echo "  ✓ HF_TOKEN"
[ -n "$OPENROUTER_API_KEY" ] && echo "  ✓ OPENROUTER_API_KEY"
[ -n "$DEBUG_API_TRUSTYPANGOLIN" ] && echo "  ✓ DEBUG_API_TRUSTYPANGOLIN"