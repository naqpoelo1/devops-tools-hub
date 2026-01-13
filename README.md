# DevOps Tools Hub

An **All-in-One** web application for DevOps teams and Developers, providing various utility tools, a code security scanner (SonarQube), and configuration generators in a single, modern, centralized interface.

## 🚀 Key Features

### 🛡️ Security & Code Quality
*   **Repo Scanner**: Graphical interface to run SonarQube Scanner on Git repositories. Supports parameter customization (*exclusions, inclusions, branch*).
*   **GitHub Access Checker**: Verify user roles/permissions on specific GitHub organizations or repositories.
*   **Password & Hash Generator**: Instantly generate strong passwords and hashes (MD5, SHA256, Bcrypt).

### 🛠️ Developer Utilities
*   **Diff Checker**: Compare two text/code blocks to see differences.
*   **Formatters**: JSON Beautifier, SQL Formatter, YAML Linter.
*   **Converters**: Base64, URL Encoder, Time Converter, JSON to Go/C/SQL/YAML.
*   **Calculators**: IP Calculator (Subnetting), Chmod Calculator.

### ⚙️ Automation & DevOps
*   **Repo Automation Setup**: Redirect to external tools for workflow & Helm automation.
*   **Dockerfile Generator**: Generate optimized Dockerfiles for various stacks.
*   **Crontab Generator**: Visual schedule builder.

## 📦 Installation & Deployment

### Using Podman / Docker (Recommended)

1.  **Clone Repository**
    ```bash
    git clone https://github.com/username/devops-tools-hub.git
    cd devops-tools-hub
    ```

2.  **Configure Environment**
    ```bash
    cp .env-example .env
    # Edit .env and adjust values
    ```

3.  **Build and Run (Podman)**
    ```bash
    # Build image
    podman build -t devops-tools-hub .

    # Run container (with volume for screenshots)
    podman run -d \
      --name devops-tools-hub \
      -p 5000:5000 \
      --env-file .env \
      -v "$(pwd)/static/screenshots:/app/static/screenshots" \
      devops-tools-hub
    ```

4.  **Build and Run (Docker Compose)**
    ```bash
    docker-compose up -d --build
    ```

### Manual Installation (Local)
1.  **Setup Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
2.  **Run**
    ```bash
    python run.py
    ```

## 🔧 White Labeling & Customization

The application supports full white-labeling via `.env` without modifying the source code.

### 🎨 Identity
*   **App Title**: `APP_TITLE="Your Hub Name"`
*   **Description**: `APP_DESCRIPTION="Internal portal for engineering"`
*   **Logo**: Change `APP_LOGO` to a URL or local path (e.g., `/static/images/logo.svg`).
*   **Favicon**: Change `APP_FAVICON`.

### 🎛️ Feature Toggles
You can dynamically show/hide or enable/disable specific integrated tools:
*   `ENABLE_REPO_SCANNER=true/false`
*   `ENABLE_STIRLING_PDF=true/false`
*   `ENABLE_REPO_AUTOMATION=true/false`
*   `ENABLE_FILE_COMPRESSOR=true/false`

*Note: Tools that require an external URL will also check if that URL is configured before appearing active.*

## 📖 Configuration Guide (.env)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `FLASK_SECRET_KEY` | Secret key for Flask security. | (Required) |
| `SONAR_HOST_URL` | Your SonarQube server URL. | - |
| `SONAR_LOGIN_TOKEN` | Token for Sonar scanner. | - |
| `REPO_AUTOMATION_FE_URL`| External URL for automation tool. | - |
| `STIRLING_STUDIO_URL` | URL for PDF manipulation tool. | - |
| `GITHUB_TOKEN` | GitHub PAT for API access. | - |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO).| INFO |

## 📄 License
This project is distributed under the MIT License.