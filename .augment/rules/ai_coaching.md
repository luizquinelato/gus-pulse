---
type: "manual"
---

# Comprehensive AI Development Guide for Pulse Platform

**Essential guidance for AI assistants working on the Pulse Platform codebase**

## 📖 Project Context Instructions

### Primary Reading: Core Documentation
📖 **Primary Reading**: Core documentation at `/docs/` + service READMEs
📋 **Secondary Reading**: Service-specific documentation in `services/*/docs/`

### 📝 Documentation Standards (Updated 2025-01-07):
- **Naming Convention**: All documentation uses lowercase with hyphens (architecture.md, security-authentication.md)
- **Location**: Core docs in `/docs/`, service-specific docs in `services/*/docs/`
- **Cross-References**: Always use lowercase file names in links
- **Consolidated Security**: All security content is in `docs/security-authentication.md`

### 🚨 Critical Architecture Rules:
- **Client Isolation**: ALL database queries must filter by client_id
- **Authentication Flow**: All services authenticate through Backend Service (no direct frontend-ETL)
- **Deactivated Records**: Exclude data connected to deactivated records at ANY level
- **Test File Cleanup**: Delete test scripts after execution unless explicitly requested to keep
- **Migration Pattern**: Update existing migration 0001 instead of creating new migrations
- **No Compatibility Code**: NEVER keep backward compatibility code - always fix as new (fresh platform approach)

### Environment Configuration:
- **Root .env**: Used by Docker Compose, startup scripts, and service configuration loading
- **Service Priority**: Services prioritize root-level .env, then service-specific overrides
- **Multi-Instance**: Use CLIENT_NAME environment variable for client-specific ETL instances
- **Package Management**: Always use package managers (npm, pip, etc.) - never edit package files manually
- **Centralized Requirements**: Use `python scripts/setup_envs.py` to install all Python and Node dependencies

## 🎯 Platform Overview

### Service Architecture:
- **Backend Service**: User identity, authentication, permissions, API gateway ONLY
- **ETL Service**: Business data, analytics, job orchestration, admin interface ONLY
- **Frontend**: User interface, token management, real-time updates
- **Auth Service**: Centralized authentication, OAuth-like flow, OKTA integration ready

### Security & Authentication:
- **Centralized authentication** via Backend Service (no direct frontend-ETL)
- **JWT token management** with shared secret across services, includes `client_id`
- **Session-based validation** with database-backed sessions + Redis caching
- **ALL ETL functionality** requires admin credentials
- **RBAC**: Role-based access control with granular permissions

### 🌐 Current Platform Configuration:
- **Frontend**: Port 3000 (Vite dev server)
- **Backend**: Port 3001 (authentication & API)
- **ETL Service**: Port 8000 (dev), 8001+ (multi-instance)
- **Auth Service**: Port 4000 (centralized auth)
- **Database**: PostgreSQL primary (5432) + replica (5433) with streaming replication
- **Cache**: Redis (6379) for sessions and caching
- **ETL Routes**: /home (not /dashboard)
- **Job Statuses**: READY, PENDING, RUNNING, FINISHED, PAUSED

### Service Communication Flow
```
Frontend → Backend Service ← ETL Service
    ↓           ↓              ↓
    Auth Service → Database (Primary/Replica)
```

## 🤖 AI Development Standards (Phase 1+)

### AI Architecture Principles
- **Phase-Based Implementation**: Follow AI Evolution Plan phases strictly
- **Backward Compatibility**: All AI enhancements must preserve existing functionality
- **Vector-First Design**: All business tables include vector columns for future AI capabilities
- **ML Monitoring**: Comprehensive tracking of AI performance and anomalies
- **Client Isolation**: AI features respect multi-tenant architecture

### AI Database Patterns (Phase 3-1)
- **Clean PostgreSQL**: Business data only, no vector columns
- **Qdrant Integration**: Separate vector database for embeddings
- **ML Monitoring Tables**: `ai_learning_memory`, `ai_predictions`, `ai_performance_metrics`, `ml_anomaly_alert`
- **Vector Tracking**: `qdrant_vectors` table tracks vector references
- **3-Database Architecture**: Primary PostgreSQL + Replica + Qdrant

### AI Architecture (Phase 3-1)
```python
# Clean models with separate vector storage in Qdrant
class Issue(Base):
    # ... business fields only ...
    # Vectors stored in Qdrant, tracked via QdrantVector table

    def to_dict(self):
        result = {
            # ... business fields only ...
        }
        return result
```

### ML Monitoring Integration
- **Performance Metrics**: Track AI system performance across all services
- **Learning Memory**: Capture user feedback and corrections for continuous improvement
- **Anomaly Detection**: Automated detection and alerting for ML-related issues
- **Prediction Logging**: Track ML model predictions and accuracy over time

### AI Service Communication
- **Phase 1**: Infrastructure prepared, AI service not yet implemented
- **Phase 2+**: RESTful API communication with dedicated AI service
- **Health Checks**: Monitor AI infrastructure and service availability
- **Error Handling**: Graceful degradation when AI features are unavailable

## 🔧 Development Standards

### Fresh Platform Approach
- **No Backward Compatibility**: This is a fresh platform - always implement the correct solution immediately
- **No Legacy Support**: Don't create mapping functions, compatibility layers, or transition code
- **Direct Implementation**: Update all references to use the new approach consistently
- **Clean Architecture**: Avoid technical debt from day one by implementing proper patterns immediately

### Database Patterns (Phase 3-1)
- **Client Isolation**: ALL tables include `client_id` for multi-tenant separation
- **Queries**: Always filter by `client_id` in database operations
- **Migrations**: Update existing migration 0001_initial_db_schema.py instead of creating new migrations
- **Deactivated Records**: Exclude data connected to deactivated records at ANY level
- **Database Router**: Use primary for writes, replica for analytics reads
- **Clean Architecture**: Business data in PostgreSQL, vectors in Qdrant
- **ML Monitoring**: Use dedicated ML monitoring tables for AI performance tracking



## 🏗️ Service-Specific Guidelines

### Backend Service (Port 3001)
- **Purpose**: User identity, authentication, permissions ONLY
- **Database**: Primary for writes, replica for analytics reads
- **APIs**: Unified interface for frontend and ETL service
- **Auth**: JWT token validation and session management

### ETL Service (Port 8000)
- **Purpose**: Business data, analytics, job orchestration ONLY
- **Routes**: Use `/home` not `/dashboard`, no `/admin` prefix (entire service is admin-only)
- **Job Statuses**: READY, PENDING, RUNNING, FINISHED, ERROR, PAUSED
- **Client Context**: Automatic client-specific logging with CLIENT_NAME environment variable
- **Scripts**: Keep `run_etl.py` and `run_etl.bat` - they provide clean shutdown handling
- **WebSocket**: Real-time job progress at `/ws/progress/{job_name}`

### Frontend (Port 3000)
- **Auth Flow**: JWT token management with shared sessions across services
- **Real-time**: WebSocket integration for live updates
- **Branding**: Client-specific color schemas and logos
- **Navigation**: Home/DORA Metrics/Engineering Analytics/Settings structure

## 🔄 Job Management & Orchestration

### Job Control Patterns
- **Force Stop**: Enable only when job is running, disable others, instant termination
- **State Management**: When one job finishes, keep other job as PAUSED if it was PAUSED
- **Recovery**: Separate 'sleep' orchestrator job for retry configuration (5-30 min intervals)
- **Cancellation**: Add checks at each pagination request for graceful termination

### Job Status Flow
```
READY → PENDING → RUNNING → FINISHED
          ↓
        PAUSED (can resume to RUNNING)
```

## 🎨 UI/UX Standards

### Design System
- **Target**: Enterprise B2B SaaS for C-level executives
- **Colors**: 5-color schema with **12 combinations per client** (2 modes × 2 themes × 3 accessibility levels)
  - **Modes**: default, custom
  - **Themes**: light, dark
  - **Accessibility**: regular, AA, AAA compliance
- **Storage**: Unified `client_color_settings` table with complete color variants
- **Typography**: Inter font, clean minimalism
- **Auto-Calculation**: Optimal text colors, contrast ratios, gradient colors, theme-adaptive variants

### Component Standards
- **Modals**: Consistent black/dark background style
- **Buttons**: Universal CRUD colors (btn-crud-create for green, etc.)
- **Controls**: Smaller control buttons than status badges
- **Forms**: Dropdown lists over text inputs for predefined options
- **Headers**: ETL service uses 'PEM' branding, page headers in CAPS
- **Tables - "No Data" State**: Always show table headers and display "no data" message inside tbody (not replacing the table)
  - Use light background: `!bg-[#f9fafb]` (light theme) and `!bg-[#1e1e1e]` (dark theme)
  - Pattern: `<tbody>{data.length === 0 ? <tr><td colSpan={N}>No data message</td></tr> : data.map(...)}</tbody>`
  - Consistent across all mapping pages (WIT Hierarchies, WIT Mappings, Status Mappings, Workflow Steps, Workflows, Custom Fields)

## 📁 File Management Standards

### Documentation Files
- **NEVER create documentation files proactively** - Only create when explicitly requested by user
- **No unsolicited .md files**: Do not create README.md, architecture docs, guides, or any documentation unless user asks
- **User-driven only**: Documentation creation is a user decision, not an AI initiative
- **Scope violation**: Creating documentation without request is considered scope creep

### Test Files
- **Delete After Validation**: Always remove test scripts after execution unless explicitly asked to keep
- **Clean Workspace**: Remove temporary files and maintain clean repository

### Docker Configuration
- **Production Ready**: All Dockerfiles include security best practices (non-root users, health checks)
- **Environment**: Proper environment variable handling
- **Dependencies**: Optimized build process with proper caching

### Requirements Management
- **Setup**: Use `python scripts/setup_envs.py` — installs all venvs and npm packages in one pass
- **Virtual Environments**: Per-service isolation (each service has its own `.venv`)
- **Package Managers**: NEVER edit package files manually - always use package managers
- **Requirements Structure**:
  - `requirements/install.txt` - Orchestrator: lists all service requirements files
  - `requirements/root.txt` - Root-level packages for standalone scripts (`cryptography`, `httpx`)
  - `services/backend/requirements/install.txt` - Backend dependencies (FastAPI, SQLAlchemy, ETL, AI)
  - `services/auth/requirements/install.txt` - Auth dependencies (minimal JWT-only)

## 🔍 Development Workflow

### Task Management Guidelines
**Use task management tools for complex work that benefits from structured planning:**

#### When to Use Task Lists:
- **Multi-step implementations** or refactors
- **Debugging** that requires investigating multiple areas
- **Feature development** with several components
- **Any request** with explicit requirements
- **Work that spans** multiple files or systems
- **Any work requiring 3+ distinct steps**

#### Task Management Best Practices:
- ✅ **Create tasks BEFORE starting work**, not after
- ✅ **Include ALL steps** in task list: Jira creation, implementation, documentation, release
- ✅ **Mark tasks as IN_PROGRESS** when starting them
- ✅ **Complete tasks IMMEDIATELY** after finishing them
- ✅ **Break complex work** into specific, actionable items
- ✅ **Track progress** to give visibility to the user

#### Subtask Description Guidelines:
- ✅ **Simple checklist format**: Use numbered list of implementation tasks only
- ✅ **Include**: Technical work (database changes, code updates, API development)
- ❌ **Exclude**: Jira management tasks (creation, transitions, comments)
- ❌ **Exclude**: Objectives, acceptance criteria, definition of done
- ✅ **Purpose**: Subtask is a checklist, not a comprehensive specification

#### Jira Integration Guidelines:
- 📋 **Complete Reference**: `.augment/rules/ai_jira_integration_guidelines.md`
- 🚀 **End-to-End Workflow**: `.augment/rules/jira_e2e_flow.md` (only when user explicitly requests "jira-e2e-flow")
- 🏗️ **Epic Creation Workflow**: `.augment/rules/jira_epic_flow.md` (only when user explicitly requests "jira-epic-flow" or epic creation only)
- 🔄 **Story & Task Workflow**: `.augment/rules/jira_story_flow.md` (only when user explicitly requests "jira-story-flow")
- 🎯 **Authority**: All Jira workflows are user-driven only - AI never suggests workflows autonomously

### Before Making Changes
1. **Read Documentation**: Always review `/docs/` for architecture understanding
2. **Codebase Retrieval**: Use for detailed information about code you want to edit
3. **Service Patterns**: Follow established patterns from the guides
4. **Client Context**: Ensure all operations respect client isolation

### Making Edits
1. **Conservative Approach**: Respect existing codebase patterns
2. **Database First**: Design with proper FK relationships
3. **Security**: All ETL functionality requires admin credentials
4. **Testing**: Suggest writing/updating tests after code changes

### Configuration Changes
1. **Environment Variables**: Store in `.env` files, not hardcoded
2. **Database Settings**: Use system_settings table for per-client customization
3. **Service URLs**: Make ETL endpoints configurable via .env

## 🚨 Critical Reminders

### Security
- **Never Commit Secrets**: Use .gitignore and pre-commit hooks
- **Client Isolation**: Every database query must filter by client_id
- **Authentication**: All cross-service communication through Backend Service
- **Permissions**: Validate user permissions for all operations

### Multi-Tenancy
- **Client-Specific Logging**: Separate logs per client across all services
- **Data Isolation**: Complete separation at database, application, and configuration levels
- **Feature Flags**: Client-specific feature enablement
- **Branding**: Per-client logos and color schemes

### Performance
- **Database**: Use replica for read-heavy analytics operations
- **Caching**: Leverage Redis for session and data caching
- **API Limits**: Monitor and respect external API rate limits
- **Resource Usage**: Consider resource usage during large operations

## 📚 Essential Documentation References

### Primary Reading (ALWAYS CONSULT)
- `docs/architecture.md` - System design and topology
- `docs/security-authentication.md` - Security implementation (consolidated)
- `docs/jobs-orchestration.md` - Job management and orchestration
- `docs/system-settings.md` - Configuration reference
- `docs/installation-setup.md` - Setup and deployment
- `docs/design-system.md` - Design and UX

### Service-Specific Guides
- `services/etl-service/docs/development-guide.md` - ETL development and testing
- `services/etl-service/docs/log-management.md` - Logging system
- `services/frontend-app/docs/` - Frontend architecture and design system
- `services/backend/README.md` - Backend service capabilities

### Key Architectural Decisions
- Multi-tenant SaaS with complete client isolation
- Centralized authentication with distributed validation
- Primary-replica database setup for performance
- Client-specific logging and configuration
- Enterprise-grade security and RBAC

## 📚 Quick Reference:

| Work Area | Primary Guide | Key Patterns |
|-----------|---------------|--------------|
| Authentication/Users | Core docs + Backend README | JWT, sessions, RBAC |
| Jobs/Data Processing | Core docs + ETL docs | Orchestration, WebSocket, APIs |
| Database/Security | Core docs + security-authentication.md | Client isolation, migrations, RBAC |
| UI/Frontend | Core docs + Frontend docs | React patterns, auth flow, responsive |
| Platform-wide | Core docs + Architecture guide | Service communication, multi-tenancy |

## ✅ Recent Implementations:
- **Documentation Standardization**: All docs use lowercase naming convention (2025-01-07)
- **Client-Specific Logging**: Complete across all services with automatic client context
- **Docker Enhancement**: Production-ready configurations with security best practices
- **Consolidated Security Documentation**: Single comprehensive security guide
- **Centralized Requirements**: Complete dependency management system with virtual environments
- **WebSocket Integration**: Real-time job progress monitoring across frontend and ETL services
- **AI Phase 1 Complete**: Database schema enhanced with vector columns and ML monitoring (2025-01-08)
- **ML Infrastructure**: PostgresML and pgvector extensions installed with vector indexes
- **Enhanced Models**: All unified models support vector columns and ML monitoring entities
- **AI Monitoring**: Comprehensive ML performance tracking and anomaly detection infrastructure

---

**Remember**: This platform serves enterprise clients with C-level executives. Every decision should reflect enterprise-grade quality, security, and user experience.
