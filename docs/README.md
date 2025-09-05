# PayMCP Documentation

Welcome to the PayMCP documentation! This directory contains comprehensive guides for setup, testing, and MCP integration.

## 📋 Documentation Index

### Project Information
- **[PROJECT_ORGANIZATION.md](./PROJECT_ORGANIZATION.md)** - Complete project structure and file organization guide

### Setup & Configuration
- **[SETUP_AND_TESTING_GUIDE.md](./SETUP_AND_TESTING_GUIDE.md)** - Complete setup guide for PayMCP with all providers, testing instructions, and troubleshooting

### MCP Integration
- PayMCP seamlessly integrates with MCP's built-in Context system - no additional setup required

### MCP Testing  
- **[MCP_TESTING_README.md](./MCP_TESTING_README.md)** - Quick start guide for MCP server testing with usage examples
- **[MCP_TEST_SCRIPTS_DEEP_DIVE.md](./MCP_TEST_SCRIPTS_DEEP_DIVE.md)** - Detailed technical analysis of all MCP test scripts

## 🚀 Quick Start

### 1. Initial Setup
```bash
# Follow the complete setup guide
cat docs/SETUP_AND_TESTING_GUIDE.md
```

### 2. Test MCP Server
```bash
# Quick test
python tests/mcp/test_mcp_simple.py

# Comprehensive testing  
python tests/mcp/test_mcp_server.py
```

## 📁 Related Directories

- **`tests/mcp/`** - MCP integration tests for server validation
- **`tests/unit/`** - Unit tests for individual components
- **`scripts/`** - Provider testing scripts and utilities  
- **`src/paymcp/providers/paypal/`** - PayPal provider with its own README

## 🔗 External Resources

- [Model Context Protocol (MCP) Specification](https://spec.modelcontextprotocol.io/)
- [PayPal Developer Documentation](https://developer.paypal.com/)
- [Stripe API Documentation](https://stripe.com/docs/api)

## 📖 Documentation Types

| Type | Purpose | Audience |
|------|---------|----------|
| **Project Info** | Structure & organization | Contributors |
| **Setup Guide** | Installation & configuration | All users |
| **MCP Integration** | Built-in Context support | All users |
| **MCP Testing** | Server testing & validation | Developers |
| **Deep Dive** | Technical implementation details | Advanced users |

## 💡 Navigation Tips

- Start with **SETUP_AND_TESTING_GUIDE.md** for initial setup
- Use **MCP_TESTING_README.md** for quick MCP testing 
- Refer to **MCP_TEST_SCRIPTS_DEEP_DIVE.md** for advanced usage
- Check provider-specific READMEs for detailed configuration