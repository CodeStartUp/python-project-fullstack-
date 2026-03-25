#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_header() {
    echo ""
    echo "========================================"
    echo "  $1"
    echo "========================================"
    echo ""
}

# Check if running on Linux or macOS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    print_info "Detected OS: $OS"
}

# Check and install Docker
install_docker() {
    print_header "Checking Docker Installation"
    
    if command -v docker &> /dev/null; then
        print_message "Docker is already installed"
        docker --version
        return 0
    fi
    
    print_warning "Docker is not installed. Installing Docker..."
    
    if [[ "$OS" == "linux" ]]; then
        # Install Docker on Linux
        print_info "Installing Docker on Linux..."
        
        # Update package index
        sudo apt-get update
        
        # Install prerequisites
        sudo apt-get install -y \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Add Docker's official GPG key
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Set up repository
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
            $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker Engine
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
        # Add current user to docker group
        sudo usermod -aG docker $USER
        
        print_warning "Please log out and back in for Docker group changes to take effect"
        
    elif [[ "$OS" == "macos" ]]; then
        # Install Docker on macOS using Homebrew
        print_info "Installing Docker on macOS..."
        
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            print_error "Homebrew is not installed. Please install Homebrew first:"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
        
        # Install Docker via Homebrew
        brew install --cask docker
        
        print_warning "Please open Docker.app from Applications folder to complete installation"
        print_warning "After Docker is running, re-run this script"
        exit 0
    fi
    
    # Wait for Docker to start
    print_info "Waiting for Docker to start..."
    sleep 5
    
    # Start Docker service on Linux
    if [[ "$OS" == "linux" ]]; then
        sudo systemctl start docker || sudo service docker start
    fi
    
    # Verify installation
    if command -v docker &> /dev/null; then
        print_message "Docker installed successfully"
        docker --version
    else
        print_error "Docker installation failed"
        exit 1
    fi
}

# Start MongoDB container
start_mongodb() {
    print_header "Starting MongoDB Container"
    
    # Check if container already exists
    if docker ps -a | grep -q mongodb-hwid; then
        if docker ps | grep -q mongodb-hwid; then
            print_message "MongoDB container is already running"
        else
            print_info "Starting existing MongoDB container..."
            docker start mongodb-hwid
            print_message "MongoDB container started"
        fi
    else
        print_info "Creating and starting MongoDB container..."
        docker run -d \
            --name mongodb-hwid \
            --restart unless-stopped \
            -p 27017:27017 \
            -v mongodb-data:/data/db \
            mongo:6.0
        
        print_message "MongoDB container created and started"
    fi
    
    # Wait for MongoDB to be ready
    print_info "Waiting for MongoDB to be ready..."
    sleep 5
    
    # Test MongoDB connection
    if docker exec mongodb-hwid mongosh --eval "db.adminCommand('ping')" &> /dev/null; then
        print_message "MongoDB is ready"
    else
        print_warning "MongoDB may not be fully ready yet"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    print_header "Setting Up Python Environment"
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_message "Python found: $PYTHON_VERSION"
    else
        print_error "Python 3 is not installed"
        print_info "Please install Python 3.8+ from https://www.python.org/downloads/"
        exit 1
    fi
    
    # Create virtual environment
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Do you want to recreate it? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
            python3 -m venv venv
            print_message "Virtual environment recreated"
        fi
    else
        python3 -m venv venv
        print_message "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements
    print_info "Installing Python packages..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_message "Packages installed from requirements.txt"
    else
        # Install packages individually if requirements.txt doesn't exist
        print_info "Installing packages individually..."
        pip install fastapi==0.104.1
        pip install "uvicorn[standard]==0.24.0"
        pip install pymongo==4.5.0
        pip install python-multipart==0.0.6
        pip install passlib==1.7.4
        pip install "python-jose[cryptography]==3.3.0"
        pip install bcrypt==4.0.1
        pip install "pydantic[email]==2.4.2"
        pip install python-dotenv==1.0.0
        pip install jinja2==3.1.2
        pip install aiofiles==23.2.1
        print_message "All packages installed"
    fi
}

# Create environment configuration
create_env_file() {
    print_header "Creating Configuration"
    
    if [ ! -f ".env" ]; then
        cat > .env << 'EOL'
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=hwid_auth_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
APP_NAME=HWID Authentication System
DEBUG=True
EOL
        print_message ".env file created"
    else
        print_message ".env file already exists"
    fi
}

# Create run script
create_run_script() {
    print_header "Creating Run Script"
    
    cat > run_app.sh << 'EOF'
#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if MongoDB is running
if ! docker ps | grep -q mongodb-hwid; then
    echo "Starting MongoDB..."
    docker start mongodb-hwid
    sleep 3
fi

# Run the application
echo "Starting HWID Authentication System..."
echo "Access at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
EOF
    
    chmod +x run_app.sh
    print_message "Created run_app.sh"
    
    # Create stop script
    cat > stop_app.sh << 'EOF'
#!/bin/bash

echo "Stopping application..."
pkill -f uvicorn || true
echo "Application stopped"

read -p "Do you want to stop MongoDB container? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop mongodb-hwid
    echo "MongoDB stopped"
fi
EOF
    
    chmod +x stop_app.sh
    print_message "Created stop_app.sh"
}

# Create requirements.txt if it doesn't exist
create_requirements() {
    if [ ! -f "requirements.txt" ]; then
        cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pymongo==4.5.0
python-multipart==0.0.6
passlib==1.7.4
python-jose[cryptography]==3.3.0
bcrypt==4.0.1
pydantic[email]==2.4.2
python-dotenv==1.0.0
jinja2==3.1.2
aiofiles==23.2.1
EOF
        print_message "Created requirements.txt"
    fi
}

# Check and create necessary directories
create_directories() {
    print_header "Creating Project Structure"
    
    mkdir -p templates static/css static/js
    
    print_message "Created directories: templates, static/css, static/js"
}

# Verify all files exist
verify_files() {
    print_header "Verifying Project Files"
    
    REQUIRED_FILES=("main.py" "auth.py" "database.py" "models.py" "config.py")
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "$file" ]; then
            print_message "✓ $file exists"
        else
            print_error "✗ $file is missing"
            exit 1
        fi
    done
    
    print_message "All required files present"
}

# Main installation process
main() {
    clear
    print_header "HWID Authentication System - Complete Setup"
    
    # Detect OS
    detect_os
    
    # Verify project files
    verify_files
    
    # Create requirements.txt
    create_requirements
    
    # Create directories
    create_directories
    
    # Install Docker and start MongoDB
    install_docker
    start_mongodb
    
    # Setup Python environment
    setup_python_env
    
    # Create configuration
    create_env_file
    
    # Create run scripts
    create_run_script
    
    # Create .gitignore
    if [ ! -f ".gitignore" ]; then
        cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
*.db
*.sqlite
.DS_Store
.vscode/
.idea/
EOF
        print_message "Created .gitignore"
    fi
    
    print_header "Setup Complete!"
    echo ""
    print_message "To start the application:"
    echo "  1. Run: ./run_app.sh"
    echo "  2. Or manually: source venv/bin/activate && uvicorn main:app --reload"
    echo ""
    print_message "To stop the application:"
    echo "  1. Press Ctrl+C in the running terminal"
    echo "  2. Or run: ./stop_app.sh"
    echo ""
    print_message "Access the application:"
    echo "  - Web Interface: http://localhost:8000"
    echo "  - API Documentation: http://localhost:8000/docs"
    echo ""
    
    # Ask if user wants to start the app now
    read -p "Do you want to start the application now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./run_app.sh
    fi
}

# Run main function
main
EOF

# Make the script executable
chmod +x setup.sh