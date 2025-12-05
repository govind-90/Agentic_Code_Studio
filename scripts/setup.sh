#!/bin/bash

# Agentic Code Studio - Setup Script

set -e

echo "🚀 Setting up Agentic Code Studio..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.10+ is required. Found: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"

# Check if UV is installed
echo ""
echo "📦 Checking UV package manager..."
if ! command -v uv &> /dev/null; then
    echo "⚠️  UV not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
echo "✅ UV is installed"

# Create virtual environment
echo ""
echo "🔧 Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping..."
else
    uv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source .venv/bin/activate || . .venv/Scripts/activate

# Install dependencies
echo ""
echo "📚 Installing dependencies..."
uv pip install -e .
echo "✅ Dependencies installed"

# Create .env file if not exists
echo ""
echo "⚙️  Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ .env file created from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your GOOGLE_API_KEY"
    echo "   Get your API key from: https://aistudio.google.com/app/apikey"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p logs outputs outputs/sessions outputs/generated_code
echo "✅ Directories created"

# Check PostgreSQL (optional)
echo ""
echo "🗄️  Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL is installed"
    
    # Try to connect
    if psql -h localhost -U postgres -c "\q" 2>/dev/null; then
        echo "✅ PostgreSQL is running"
    else
        echo "⚠️  PostgreSQL is not running. Start it with:"
        echo "   sudo systemctl start postgresql  # Linux"
        echo "   brew services start postgresql   # macOS"
    fi
else
    echo "⚠️  PostgreSQL not found (optional for database-related code generation)"
    echo "   Install with:"
    echo "   sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian"
    echo "   brew install postgresql                         # macOS"
fi

# Check Maven (optional)
echo ""
echo "☕ Checking Maven..."
if command -v mvn &> /dev/null; then
    maven_version=$(mvn --version | head -n1)
    echo "✅ Maven is installed: $maven_version"
else
    echo "⚠️  Maven not found (optional for Java code generation)"
    echo "   Install with:"
    echo "   sudo apt install maven  # Ubuntu/Debian"
    echo "   brew install maven      # macOS"
fi

# Final message
echo ""
echo "✨ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env and add your GOOGLE_API_KEY"
echo "2. Activate virtual environment: source .venv/bin/activate"
echo "3. Run the application: streamlit run src/ui/streamlit_app.py"
echo ""
echo "   Or use the convenience script: ./scripts/run.sh"
echo ""
echo "Happy coding! 🚀"