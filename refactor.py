import os
import shutil
import stat

def on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except:
        pass

def replace_in_file(path, replacements):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        # fallback to utf-16 or ignore if binary
        try:
            with open(path, "r", encoding="utf-16") as f:
                content = f.read()
        except Exception:
            return
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        try:
            # write back with same encoding
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {path}")
        except Exception as e:
            print(f"Failed to write {path}: {e}")

def process_service(service_path, is_ecom):
    print(f"Processing {service_path}")
    os.chdir(service_path)
    
    utils_dir = "utils"
    if not os.path.exists(utils_dir):
        os.makedirs(utils_dir)
        with open(os.path.join(utils_dir, "__init__.py"), "w") as f:
            f.write("")
            
    # 1. move core/config.py and core/logging.py to utils
    if os.path.exists("core/config.py"):
        shutil.move("core/config.py", f"{utils_dir}/config.py")
    if os.path.exists("core/logging.py"):
        shutil.move("core/logging.py", f"{utils_dir}/logging.py")
        
    # delete old core
    if os.path.exists("core") and (is_ecom and os.path.exists("api") or not is_ecom and os.path.exists("search")):
        # If the app folder (api/search) still exists, this means core hasn't been replaced yet
        try:
            shutil.rmtree("core", onerror=on_rm_error)
        except Exception as e:
            print(f"Failed to delete core: {e}")
            pass
        
    # 2. rename api/search to core
    app_name = "api" if is_ecom else "search"
    if os.path.exists(app_name):
        try:
            os.rename(app_name, "core")
            print(f"Renamed {app_name} to core")
        except Exception as e:
            print(f"Failed to rename {app_name} to core: {e}")
        
    # 3. rename project dir to config
    proj_dir = "ecom_project" if is_ecom else "search_project"
    if os.path.exists(proj_dir):
        try:
            os.rename(proj_dir, "config")
            print(f"Renamed {proj_dir} to config")
        except Exception as e:
            print(f"Failed to rename {proj_dir} to config: {e}")
        
    # 4. Search and replace in all python, config, md files
    replacements = [
        ("core.config", "utils.config"),
        ("core.logging", "utils.logging"),
        (f"{proj_dir}.settings", "config.settings"),
        (f"{proj_dir}.urls", "config.urls"),
        (f"{proj_dir}.wsgi", "config.wsgi"),
        (f"{proj_dir}", "config"),
    ]
    if is_ecom:
        replacements.extend([
            ("from api.", "from core."),
            ("from api ", "from core "),
            ("import api.", "import core."),
            ("import api", "import core"),
            ("name = 'api'", "name = 'core'"),
            ("'api'", "'core'"),
            ('"api"', '"core"')
        ])
    else:
        replacements.extend([
            ("from search.", "from core."),
            ("from search ", "from core "),
            ("import search.", "import core."),
            ("import search", "import core"),
            ("name = 'search'", "name = 'core'"),
            ("'search'", "'core'"),
            ('"search"', '"core"')
        ])
        
    for dp, _, filenames in os.walk("."):
        if "__pycache__" in dp or ".git" in dp or "venv" in dp:
            continue
        for f in filenames:
            if f.endswith(".py") or f.endswith(".md") or f.endswith(".txt"):
                path = os.path.join(dp, f)
                replace_in_file(path, replacements)

# Execute
process_service("c:/project/bookstore-microservice/e-com-service", True)
process_service("c:/project/bookstore-microservice/search-service", False)
print("Done!")
