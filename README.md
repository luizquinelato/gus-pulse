# Pulse Platform

**Enterprise-Grade DevOps Analytics & Project Intelligence Platform**

Pulse Platform is a comprehensive, multi-tenant SaaS solution designed for senior leadership and C-level executives to gain deep insights into their software development lifecycle. Built with enterprise-scale architecture, the platform provides real-time analytics, DORA metrics, and intelligent project tracking across multiple tenants and teams.

## 🚀 Platform Overview

### What is Pulse Platform?

Pulse Platform transforms raw development data into actionable business intelligence. By integrating with your existing tools (Jira, GitHub, and more), it provides a unified view of your engineering performance, project health, and delivery metrics.

**Key Capabilities:**
- **DORA Metrics**: Lead Time, Deployment Frequency, Change Failure Rate, Recovery Time
- **Project Intelligence**: Real-time project status, risk assessment, delivery predictions
- **Multi-Source Integration**: Seamless data aggregation from Jira, GitHub, and other tools
- **Executive Dashboards**: C-level friendly visualizations and KPIs
- **Multi-Tenant Architecture**: Secure tenant isolation with enterprise-grade security
### Why Pulse Platform?

**🏢 Enterprise-Ready**
- Multi-tenant SaaS architecture with complete tenant isolation
- Primary-replica database setup for high availability and performance
- Comprehensive RBAC system with granular permissions
- Tenant-specific logging and audit trails

**📊 Business Intelligence**
- Transform development metrics into business insights
- Identify bottlenecks and optimization opportunities
- Track delivery performance against commitments
- Predictive analytics for project outcomes

**🔧 Robust & Scalable**
- Microservices architecture with independent scaling
- Event-driven job orchestration with recovery strategies
- Real-time WebSocket updates and notifications
- Docker-based deployment with production-ready configurations

**🎨 Executive Experience**
- Clean, professional UI designed for senior leadership
- Customizable color schemes and branding per tenant
- User-specific light/dark mode preferences with enterprise aesthetics
- Mobile-responsive design for on-the-go access

## 🏗️ Architecture Highlights

### Five-Tier Microservices Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Application                         │
│                   (React/TypeScript - Port 5173)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Executive Dashboards    🎨 Client Branding                  │
│  📈 DORA Metrics           🌙 Dark/Light Mode                   │
│  🔧 Admin Interface        📱 Responsive Design                 │
│  🤖 AI Features            🔍 Semantic Search                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
│  Backend        │              │  Frontend ETL   │              │  Auth Service   │
│  Service        │◄────────────►│  (React/TS)     │              │  (FastAPI)      │
│  (FastAPI)      │              │  Port: 3333     │              │  Port: 4000     │
│  Port: 3001     │              │                 │              │                 │
│                 │              │ • Job Cards     │              │ • JWT Tokens    │
│ • Authentication│              │ • WIT Mgmt      │              │ • User Auth     │
│ • User Mgmt     │              │ • Status Mgmt   │              │ • OKTA Ready    │
│ • Session Mgmt  │              │ • Integrations  │              │ • SSO Flow      │
│ • API Gateway   │              │ • Dark Mode     │              │ • Validation    │
│ • Client Mgmt   │              │ • Responsive    │              │                 │
│ • ML Monitoring │              │                 │              │                 │
│ • AI Operations │              │                 │              │                 │
│ • Flexible AI   │              │                 │              │                 │
│ • Embeddings    │              │                 │              │                 │
│ • Chat Agents   │              │                 │              │                 │
│ • Vector Ops    │              │                 │              │                 │
│ • JSON Routing  │              │                 │              │                 │
│ • RBAC & JWT    │              │                 │              │                 │
│ • ETL Endpoints │              │                 │              │                 │
│   /app/etl/*    │              │                 │              │                 │
└─────────────────┘              └─────────────────┘              └─────────────────┘
                    │                       │
                    └───────────────────────┼─────┐
                                           │     │
                    ┌──────────────────────┘     │
                    ▼                            ▼
┌─────────────────────────────────────┐    ┌─────────────────┐
│           Data Layer                │    │  ETL Service    │
│                                     │    │  (LEGACY)       │
│  🗄️ PostgreSQL Primary/Replica      │    │  Port: 8000     │
│     (Ports: 5432/5433)              │    │                 │
│  🔄 Redis Cache                     │    │ ⚠️ DO NOT USE   │
│     (Port: 6379)                    │    │ • Old Monolith  │
│  🐰 RabbitMQ Queue                  │    │ • Jinja2 HTML   │
│     (Ports: 5672/15672)             │    │ • Legacy Backup │
│  🤖 Qdrant Vector Database          │    │                 │
│     (Ports: 6333/6334)              │    │                 │
│  📁 File Storage                    │    │ • Jinja2 HTML   │
│                                     │    │ • Legacy Backup │
└─────────────────────────────────────┘    │ • Reference Only│
                                           │                 │
                                           └─────────────────┘
```

**Technology Stack:**
- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Backend**: FastAPI, SQLAlchemy, Pandas/NumPy, WebSockets, Redis, AI Integration
- **Database**: PostgreSQL with primary-replica setup, Qdrant Vector DB
- **Infrastructure**: Docker, Redis caching, RabbitMQ queues, real-time WebSocket updates

## 🧭 Navigation UX
- All sidebar and submenu items support native browser interactions: right-click → Open link in new tab, middle-click, and Cmd/Ctrl+click. We achieve this by rendering real anchor links (React Router Links in the frontend; <a href> in ETL).

## 🎨 Design System & Colors
- Backend exposes both default_colors and custom_colors; the frontend and ETL set CSS vars accordingly.
- Enterprise-grade color schemes with tenant-specific branding support.

**Enterprise Features:**
- PostgreSQL primary-replica setup for high availability
- Redis caching for optimal performance
- **Secure API-only authentication service**
- **Cross-service authentication and OKTA integration ready**
- JWT-based authentication with session management
- Tenant-specific data isolation and security
- Real-time job monitoring and recovery capabilities

## 📚 Documentation

This platform includes comprehensive documentation to help you understand, deploy, and maintain the system:

### Core Documentation

| Document | Description |
|----------|-------------|
| **[ARCHITECTURE](docs/ARCHITECTURE_NEW.md)** | Complete system design, microservices topology, multi-tenancy, database architecture, deployment configurations |
| **[SECURITY](docs/SECURITY.md)** | Enterprise security, RBAC, JWT authentication, tenant isolation, compliance, security best practices |
| **[INSTALLATION](docs/INSTALLATION.md)** | Complete deployment guide, requirements, database setup, Docker configurations, production deployment |
| **[AI & VECTORIZATION](docs/AI.md)** | AI integration, embedding models, vector search, semantic capabilities, Qdrant configuration |
| **[ETL & QUEUE SYSTEM](docs/ETL.md)** | ETL architecture, job orchestration, RabbitMQ queues, Jira/GitHub integrations, data processing |

### API Documentation

The platform provides comprehensive API documentation through OpenAPI/Swagger:

- **Auth Service**: `http://localhost:4000/health` (API-only authentication backend)
- **Backend Service API**: `http://localhost:3001/docs` (Core business logic and ETL endpoints)
- **Frontend ETL**: `http://localhost:3333` (ETL management interface)
- **Legacy ETL Service**: `http://localhost:8000/docs` (⚠️ DEPRECATED - Reference only)

## 🎯 Target Audience

**Primary Users:**
- **C-Level Executives**: Strategic insights and high-level metrics
- **Engineering Directors**: Team performance and delivery tracking
- **Project Managers**: Project health and timeline monitoring
- **DevOps Teams**: System administration and maintenance

**Use Cases:**
- Executive reporting and board presentations
- Engineering performance optimization
- Project delivery predictability
- Resource allocation decisions
- Technical debt and risk assessment

## 🌟 Key Differentiators

**Enterprise-Grade Security**
- Multi-tenant architecture with complete tenant isolation
- Comprehensive audit logging and compliance features
- Role-based access control with granular permissions

**Intelligent Analytics**
- DORA metrics with industry benchmarking
- Predictive project delivery analytics
- Automated risk detection and alerting

**Seamless Integration**
- Native Jira and GitHub connectors
- Extensible architecture for additional integrations
- Real-time data synchronization

**Executive Experience**
- Purpose-built for senior leadership consumption
- Clean, professional interface with customizable branding
- Mobile-responsive design for executive mobility

## 🚀 Getting Started

### **⚡ Quick Setup (Recommended)**

```bash
# 1. Clone repository
git clone <repository-url>
cd pulse-platform

# 2. Install all dependencies (venvs + npm)
python scripts/setup_envs.py

# 3. Configure environment files
nano .env  # Edit with your database and API credentials

# 4. Start database and run migrations
docker-compose -f docker-compose.db.yml up -d
python services/backend/scripts/migration_runner.py --apply-all

# 5. Start services
# Backend:      cd services/backend && .venv/Scripts/activate && uvicorn app.main:app --reload --port 3001
# Auth:         cd services/auth && .venv/Scripts/activate && uvicorn app.main:app --reload --port 3002
# Frontend:     cd services/frontend && npm run dev
# Frontend ETL: cd services/frontend-etl && npm run dev
```

**What the setup script does:**
- ✅ Creates Python virtual environments for all services
- ✅ Installs all dependencies (FastAPI, pandas, numpy, websockets, etc.)
- ✅ Installs Node.js dependencies for frontend
- ✅ Copies `.env.example` files to `.env` for all services
- ✅ Cross-platform support (Windows, Linux, macOS)

### **📚 Comprehensive Guide**

For detailed setup instructions, see our [INSTALLATION Guide](docs/INSTALLATION.md) which covers:

1. **Prerequisites**: System requirements and dependencies
2. **Database Setup**: PostgreSQL primary-replica configuration
3. **Service Deployment**: Docker-based deployment strategies
4. **Initial Configuration**: Tenant setup and system settings
5. **Integration Setup**: Connecting Jira and GitHub
6. **Production Deployment**: Docker Swarm and Kubernetes configurations

## 📞 Support & Maintenance

Pulse Platform is designed for enterprise reliability with comprehensive monitoring, logging, and recovery capabilities. The platform includes:

- **Health Monitoring**: Real-time system health checks
- **Automated Recovery**: Self-healing job orchestration and AI validation
- **Comprehensive Logging**: Tenant-specific audit trails
- **Performance Metrics**: Built-in performance monitoring

---

**Built for Enterprise. Designed for Executives. Engineered for Scale.**

*Pulse Platform - Transforming Development Data into Business Intelligence*


















