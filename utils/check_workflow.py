#!/usr/bin/env python3
import sys
import json
import os
import re
try:
    import httpx
except ImportError:
    print("Error: El paquete 'httpx' es requerido. Instálalo con: pip install httpx")
    sys.exit(1)

REPO = "Eirom16/pyrolist"
API_URL = f"https://api.github.com/repos/{REPO}/actions/runs"

def load_github_token():
    # Try environment variables first
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token
    
    # Try a local token file (git-ignored)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    token_file = os.path.join(base_dir, "github_token.txt")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            return f.read().strip()
            
    # Try loading from a json if present
    token_json = os.path.join(base_dir, "github_token.json")
    if os.path.exists(token_json):
        try:
            with open(token_json, "r") as f:
                data = json.load(f)
                return data.get("token") or data.get("github_token")
        except:
            pass
            
    return None

def fetch_and_print_job_logs(job_id, job_name, failed_step_name, token):
    url = f"https://api.github.com/repos/{REPO}/actions/jobs/{job_id}/logs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    try:
        print(f"   🔄 Descargando logs para el paso fallido '{failed_step_name}'...")
        r = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        if r.status_code == 200:
            log_text = r.text
            lines = log_text.splitlines()
            
            # Clean timestamps
            clean_lines = []
            for line in lines:
                match = re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z (.*)$", line)
                if match:
                    clean_lines.append(match.group(1))
                else:
                    clean_lines.append(line)
            
            # Extract step log
            step_lines = []
            in_step = False
            norm_step = failed_step_name.lower().strip()
            
            for line in clean_lines:
                lower_line = line.lower()
                if "##[group]" in line or "##[section]" in line:
                    if in_step:
                        break  # Next step started, stop
                    if norm_step in lower_line or (norm_step.replace("run ", "") in lower_line):
                        in_step = True
                        continue
                if in_step:
                    step_lines.append(line)
            
            if len(step_lines) < 3:
                # Fallback: last 40 lines
                step_lines = clean_lines[-40:]
                print(f"\n   --- ÚLTIMAS LÍNEAS DE LOG DE TODO EL TRABAJO '{job_name}' (Fallback) ---")
            else:
                print(f"\n   --- LOGS DEL PASO FALLIDO: '{failed_step_name}' ---")
            
            error_keywords = ["error", "fail", "exception", "traceback", "fatal", "invalid", "missing", "exit code", "err:"]
            highlighted_indices = set()
            for idx, line in enumerate(step_lines):
                lower_line = line.lower()
                if any(kw in lower_line for kw in error_keywords) and not "check_workflow" in lower_line:
                    highlighted_indices.add(idx)
            
            for idx, line in enumerate(step_lines):
                if idx in highlighted_indices:
                    print(f"   \033[1;31m>>> {line}\033[0m")
                else:
                    print(f"       {line}")
            print(f"   --- FIN DE LOGS DE '{failed_step_name}' ---\n")
        elif r.status_code == 403:
            print(f"   ⚠️ No se pudieron descargar los logs (403 Forbidden).")
            print(f"      El token proporcionado no tiene suficientes permisos o ha expirado.")
        else:
            print(f"   ❌ No se pudieron descargar los logs. Código de respuesta: {r.status_code}")
    except Exception as e:
        print(f"   ❌ Error al descargar logs: {e}")

def get_failed_details(run_id, token=None):
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs"
    try:
        r = httpx.get(url, timeout=10.0)
        r.raise_for_status()
        jobs_data = r.json()
        
        print(f"\n=== DETALLE DE ERRORES PARA EL RUN #{run_id} ===")
        found_failure = False
        for job in jobs_data.get("jobs", []):
            if job.get("conclusion") == "failure":
                found_failure = True
                job_id = job.get("id")
                job_name = job.get("name")
                print(f"\n🔴 Trabajo Fallido: {job_name}")
                print(f"   URL: {job.get('html_url')}")
                print("   Pasos:")
                failed_step = None
                for step in job.get("steps", []):
                    status = step.get("status")
                    conclusion = step.get("conclusion")
                    icon = "✅" if conclusion == "success" else "❌" if conclusion == "failure" else "⏳" if status == "in_progress" else "⏭️"
                    
                    if conclusion == "failure":
                        failed_step = step.get("name")
                        print(f"     {icon} \033[1;31m{failed_step} (Falló)\033[0m")
                    else:
                        print(f"     {icon} {step.get('name')} ({conclusion or status})")
                
                if failed_step and token:
                    fetch_and_print_job_logs(job_id, job_name, failed_step, token)
                elif failed_step:
                    print(f"\n   💡 Para ver los detalles del error aquí mismo de forma automática,")
                    print(f"      crea un archivo 'github_token.txt' en la raíz con un token de GitHub (PAT)")
                    print(f"      o define la variable de entorno GITHUB_TOKEN.")
        if not found_failure:
            print("No se encontraron detalles de fallos individuales (posible error de inicialización del runner).")
    except Exception as e:
        print(f"Error al obtener detalles del run: {e}")

def main():
    token = load_github_token()
    if token:
        print("🔑 Token de GitHub cargado correctamente para descargar logs.")
    
    print(f"Consultando últimos workflows de {REPO}...")
    try:
        r = httpx.get(API_URL, params={"per_page": 5}, timeout=10.0)
        r.raise_for_status()
        runs = r.json().get("workflow_runs", [])
        
        if not runs:
            print("No se encontraron ejecuciones de workflows.")
            return
 
        print("\nÚltimas ejecuciones de GitHub Actions:")
        print(f"{'Run ID':<13} | {'Tag/Rama':<12} | {'Evento':<8} | {'Estado':<10} | {'Conclusión':<10}")
        print("-" * 65)
        
        for run in runs:
            run_id = run.get("id")
            branch = run.get("head_branch")
            event = run.get("event")
            status = run.get("status")
            conclusion = run.get("conclusion") or "running"
            
            # Color coding
            color = "\033[32m" if conclusion == "success" else "\033[31m" if conclusion == "failure" else "\033[33m"
            reset = "\033[0m"
            
            print(f"{run_id:<13} | {branch:<12} | {event:<8} | {status:<10} | {color}{conclusion:<10}{reset}")
            
        # Get details of the latest run if it failed
        latest_run = runs[0]
        if latest_run.get("conclusion") == "failure":
            get_failed_details(latest_run.get("id"), token)
            
    except Exception as e:
        print(f"Error al conectar con la API de GitHub: {e}")

if __name__ == "__main__":
    main()
