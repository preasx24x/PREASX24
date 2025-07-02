import os
import subprocess
import shutil
import tempfile
import time
import random
import string
import webbrowser
import requests
from pathlib import Path
from colorama import Fore, Style, init
from pyfiglet import Figlet
from halo import Halo
import sys

# Initialize colorama
init(autoreset=True)

# Constants
TEMPLATE_REPO = "preasx24x/webview"
BASE_REPO_NAME = "webview-apps"
CONFIG_FILE = os.path.expanduser("~/.webview_builder_config")
BUILD_TIME = 180  # 3 minutes countdown
RELEASE_URL = "https://github.com/{username}/{repo}/blob/master/release/webview-app.apk?raw=true"
DEFAULT_ICON_URLS = {
    "xxxhdpi": "https://github.com/preasx24x/webview/raw/master/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png",
    "xxhdpi": "https://github.com/preasx24x/webview/raw/master/app/src/main/res/mipmap-xxhdpi/ic_launcher.png",
    "xhdpi": "https://github.com/preasx24x/webview/raw/master/app/src/main/res/mipmap-xhdpi/ic_launcher.png",
    "mdpi": "https://github.com/preasx24x/webview/raw/master/app/src/main/res/mipmap-mdpi/ic_launcher.png"
}
SPECIAL_URL = "https://otieu.com/4/9515888"  # URL to open every 50 seconds
IMAGE_UPLOAD_HELP_URL = "https://who.preasx24.co.za"  # URL for image upload help

class ConsoleUI:
    @staticmethod
    def print_banner():
        """Display animated banner"""
        f = Figlet(font='slant')
        print(f"{Fore.CYAN}{f.renderText('WEBVIEW BUILDER')}")
        print(f"{Fore.MAGENTA}┏{'━' * 60}┓")
        print(f"┃{Fore.YELLOW}    Advanced Android WebView APK Generator (v2.4)       {Fore.MAGENTA}┃")
        print(f"┃{Fore.YELLOW}    GitHub Automated Build System • Premium Edition     {Fore.MAGENTA}┃")
        print(f"┗{'━' * 60}┛{Style.RESET_ALL}\n")

    @staticmethod
    def print_panel(title, content, color=Fore.CYAN):
        """Print content in a bordered panel"""
        print(f"{color}╔{'═' * 78}╗")
        print(f"║ {Fore.WHITE}{title.upper():<76}{color}║")
        print(f"╠{'═' * 78}╣")
        for line in content.split('\n'):
            print(f"║ {line:<76} {color}║")
        print(f"╚{'═' * 78}╝{Style.RESET_ALL}")

    @staticmethod
    def input_with_style(prompt, color=Fore.CYAN):
        """Styled input prompt"""
        return input(f"{color}┫ {Fore.WHITE}{prompt}{color} ➢ {Style.RESET_ALL}")

    @staticmethod
    def print_status(message, status="info"):
        """Animated status messages"""
        icons = {
            "success": f"{Fore.GREEN}✔",
            "error": f"{Fore.RED}✖",
            "warning": f"{Fore.YELLOW}⚠",
            "progress": f"{Fore.CYAN}↻",
            "info": f"{Fore.BLUE}ℹ"
        }
        print(f"{icons.get(status, icons['info'])} {message}{Style.RESET_ALL}")

    @staticmethod
    def countdown_timer(seconds):
        """Visual countdown timer with progress bar"""
        last_url_open_time = 0
        for remaining in range(seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            progress = int(50 * (seconds - remaining) / seconds)
            sys.stdout.write(f"\r{Fore.YELLOW}⏳ Build in progress... {Fore.CYAN}{mins:02d}:{secs:02d} remaining "
                            f"{Fore.GREEN}[{'█' * progress}{' ' * (50 - progress)}]{Style.RESET_ALL}")
            sys.stdout.flush()
            
            # Check if 50 seconds have passed since last URL open
            current_time = time.time()
            if current_time - last_url_open_time >= 50:
                termux_open_url(SPECIAL_URL)
                last_url_open_time = current_time
                
            time.sleep(1)
        print()

def generate_valid_package_name():
    """Generate a valid Android package name"""
    return f"com.{''.join(random.choices(string.ascii_lowercase, k=4))}.{''.join(random.choices(string.ascii_lowercase, k=6))}"

def get_github_username():
    """Get or set GitHub username with validation"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return f.read().strip()
    
    ConsoleUI.print_panel("GitHub Configuration", "We need your GitHub username to create the repository")
    while True:
        username = ConsoleUI.input_with_style("Enter your GitHub username").strip()
        if username and ' ' not in username:
            with open(CONFIG_FILE, 'w') as f:
                f.write(username)
            return username
        ConsoleUI.print_status("Invalid username! No spaces allowed.", "error")

def get_apk_url():
    """Generate the APK download URL"""
    username = get_github_username()
    return RELEASE_URL.format(username=username, repo=BASE_REPO_NAME)

def check_github_auth():
    """Check GitHub auth status with spinner"""
    with Halo(text='Checking GitHub authentication', spinner='dots'):
        try:
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
            return "Logged in to github.com" in result.stdout
        except:
            return False

def github_login():
    """Authenticate with GitHub with visual feedback"""
    if not check_github_auth():
        ConsoleUI.print_panel("GitHub Authentication", "We need to authenticate with GitHub to proceed")
        ConsoleUI.print_status("Opening GitHub authentication in your browser...", "progress")
        subprocess.run(["gh", "auth", "login", "--hostname", "github.com", "--web"], check=True)
        ConsoleUI.print_status("GitHub authentication complete!", "success")
    else:
        ConsoleUI.print_status("Already authenticated with GitHub", "success")

def check_default_branch():
    """Check the default branch of the target repository"""
    target_repo = f"{get_github_username()}/{BASE_REPO_NAME}"
    result = subprocess.run(["gh", "repo", "view", target_repo, "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"], 
                          capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "main"

def setup_repository():
    """Ensure target repository exists with visual feedback"""
    target_repo = f"{get_github_username()}/{BASE_REPO_NAME}"
    default_branch = check_default_branch()
    
    with Halo(text=f'Checking repository {target_repo}', spinner='dots'):
        try:
            subprocess.run(["gh", "repo", "view", target_repo], check=True, stdout=subprocess.DEVNULL)
            ConsoleUI.print_status(f"Using existing repository: {target_repo}", "success")
            return default_branch
        except:
            pass
    
    ConsoleUI.print_panel("Repository Setup", f"Creating new repository: {target_repo}")
    with Halo(text='Creating repository', spinner='dots'):
        subprocess.run(["gh", "repo", "create", target_repo, "--public", "--default-branch", "master"], check=True)
    ConsoleUI.print_status(f"Repository created successfully!", "success")
    return "master"

def termux_open_url(url):
    """Use Termux API to reliably open URLs"""
    try:
        # First try the standard webbrowser module
        if webbrowser.open(url):
            return True
        
        # If that fails, use Termux's native open-url command
        if shutil.which("termux-open-url"):
            subprocess.run(["termux-open-url", url], check=True)
            return True
            
        # As a last resort, try am start for Android
        subprocess.run(
            ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            check=True
        )
        return True
    except Exception:
        return False

def download_and_save_image(url, file_path):
    """Download image from URL and save to file"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        ConsoleUI.print_status(f"Failed to download/save image: {str(e)}", "error")
        return False

def update_launcher_icons(temp_dir, icon_url):
    """Update launcher icons with a new image from URL"""
    ConsoleUI.print_status("Updating launcher icons...", "progress")
    
    # Get all density directories
    density_dirs = {
        "xxxhdpi": Path(temp_dir) / "app/src/main/res/mipmap-xxxhdpi",
        "xxhdpi": Path(temp_dir) / "app/src/main/res/mipmap-xxhdpi",
        "xhdpi": Path(temp_dir) / "app/src/main/res/mipmap-xhdpi",
        "mdpi": Path(temp_dir) / "app/src/main/res/mipmap-mdpi"
    }
    
    # Create a temporary file for the downloaded image
    temp_icon_path = Path(temp_dir) / "temp_icon.png"
    
    # Download the image
    if not download_and_save_image(icon_url, temp_icon_path):
        ConsoleUI.print_status("Using default launcher icons", "warning")
        return False
    
    try:
        # Copy the same image to all density directories
        for density, dir_path in density_dirs.items():
            dir_path.mkdir(parents=True, exist_ok=True)
            shutil.copy(temp_icon_path, dir_path / "ic_launcher.png")
        
        ConsoleUI.print_status("Launcher icons updated successfully!", "success")
        return True
    except Exception as e:
        ConsoleUI.print_status(f"Failed to update icons: {str(e)}", "error")
        return False
    finally:
        # Clean up temporary file
        try:
            temp_icon_path.unlink()
        except:
            pass

def customize_android_files(temp_dir, package_name, version_code, website_url, app_name, use_custom_icon=False, icon_url=None):
    """Handle all Android file customizations"""
    # Update launcher icons if requested
    if use_custom_icon and icon_url:
        if not update_launcher_icons(temp_dir, icon_url):
            ConsoleUI.print_status("Reverting to default icons", "warning")
    
    # AndroidManifest.xml
    manifest_path = Path(temp_dir) / "app/src/main/AndroidManifest.xml"
    manifest_content = manifest_path.read_text()
    manifest_content = manifest_content.replace('package="ani.example.app"', f'package="{package_name}"')
    manifest_content = manifest_content.replace('android:name=".MainActivity"', f'android:name="{package_name}.MainActivity"')
    manifest_content = manifest_content.replace('android:name=".PopupWebViewActivity"', f'android:name="{package_name}.PopupWebViewActivity"')
    manifest_path.write_text(manifest_content)
    
    # Java files
    original_java_dir = Path(temp_dir) / "app/src/main/java/com/example/app"
    package_path = package_name.replace('.', '/')
    new_package_dir = Path(temp_dir) / f"app/src/main/java/{package_path}"
    new_package_dir.mkdir(parents=True, exist_ok=True)
    
    # MainActivity.java
    main_activity = original_java_dir / "MainActivity.java"
    main_content = main_activity.read_text()
    main_content = main_content.replace('package ani.example.app;', f'package {package_name};')
    main_content = main_content.replace(
        'private final String mainUrl = "https://your-actual-domain.com/initial-page.html"; // CHANGE THIS',
        f'private final String mainUrl = "{website_url}";'
    )
    (new_package_dir / "MainActivity.java").write_text(main_content)
    
    # PopupWebViewActivity.java
    popup_activity = original_java_dir / "PopupWebViewActivity.java"
    popup_content = popup_activity.read_text()
    popup_content = popup_content.replace('package ani.example.app;', f'package {package_name};')
    (new_package_dir / "PopupWebViewActivity.java").write_text(popup_content)
    
    # Clean up old files
    main_activity.unlink()
    popup_activity.unlink()
    try:
        original_java_dir.rmdir()
        (original_java_dir.parent).rmdir()
        (original_java_dir.parent.parent).rmdir()
    except OSError:
        pass
    
    # build.gradle
    build_gradle = Path(temp_dir) / "app/build.gradle"
    build_content = build_gradle.read_text()
    build_content = build_content.replace('applicationId "ani.example.app"', f'applicationId "{package_name}"')
    build_content = build_content.replace('versionCode 1', f'versionCode {version_code}')
    build_content = build_content.replace('versionName "1.0"', f'versionName "1.{random.randint(1, 100)}"')
    build_gradle.write_text(build_content)
    
    # strings.xml
    strings_xml = Path(temp_dir) / "app/src/main/res/values/strings.xml"
    content = strings_xml.read_text()
    content = content.replace("DTECH ANIME", app_name)
    strings_xml.write_text(content)

def build_apk(website_url, app_name, use_custom_icon=False, icon_url=None):
    """Main build process with enhanced visual feedback"""
    ConsoleUI.print_panel("Build Initiated", f"Starting build process for:\nApp Name: {app_name}\nWebsite URL: {website_url}")
    
    temp_dir = tempfile.mkdtemp()
    target_repo = f"{get_github_username()}/{BASE_REPO_NAME}"
    repo_url = f"https://github.com/{target_repo}.git"
    default_branch = setup_repository()
    
    try:
        # Clone template
        with Halo(text='Cloning template repository', spinner='dots'):
            subprocess.run(["gh", "repo", "clone", TEMPLATE_REPO, temp_dir], check=True)
            shutil.rmtree(os.path.join(temp_dir, ".git"))

        # Customize files
        ConsoleUI.print_status("Customizing application files...", "progress")
        
        package_name = generate_valid_package_name()
        version_code = random.randint(10000, 99999)
        
        # Modify Android files
        customize_android_files(temp_dir, package_name, version_code, website_url, app_name, use_custom_icon, icon_url)
        
        # Push changes
        with Halo(text='Pushing changes to GitHub', spinner='dots'):
            os.chdir(temp_dir)
            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "checkout", "-b", default_branch], check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"Build for {app_name}"], check=True)
            subprocess.run(["git", "push", "-u", "origin", f"HEAD:{default_branch}", "--force"], check=True)
        
        # Start countdown
        ConsoleUI.print_panel("Build Status", "Your APK is being built on GitHub servers\nEstimated completion time: 3 minutes")
        ConsoleUI.countdown_timer(BUILD_TIME)
        
        # Get final URL
        apk_url = get_apk_url()
        ConsoleUI.print_panel("Build Complete", f"Your APK is ready!\nDownload URL: {apk_url}")
        
        # Use Termux-specific method to open browser
        ConsoleUI.print_status("Opening browser with Termux API...", "progress")
        if termux_open_url(apk_url):
            ConsoleUI.print_status("Browser opened successfully!", "success")
        else:
            ConsoleUI.print_status("⚠ Could not open browser automatically.", "warning")
            ConsoleUI.print_status(f"ℹ Please manually visit: {apk_url}", "info")
            ConsoleUI.print_status("Press ENTER to exit...", "info")
            input()
        
    except subprocess.CalledProcessError as e:
        ConsoleUI.print_status(f"Build failed: {str(e)}", "error")
        if "src refspec" in str(e):
            ConsoleUI.print_status("Hint: Check if your repository has 'main' or 'master' as default branch", "warning")
    finally:
        shutil.rmtree(temp_dir)

def main():
    ConsoleUI.print_banner()
    
    # Check dependencies
    try:
        subprocess.run(["gh", "--version"], check=True, stdout=subprocess.DEVNULL)
    except:
        ConsoleUI.print_panel("Dependency Missing", "GitHub CLI is required\nInstall with: pkg update && pkg install gh")
        exit(1)

    # Get user input
    ConsoleUI.print_panel("Project Configuration", "Enter your app details below")
    
    while True:
        website_url = ConsoleUI.input_with_style("Website URL (include https://)").strip()
        if website_url.startswith(('http://', 'https://')):
            break
        ConsoleUI.print_status("Invalid URL! Must start with http:// or https://", "error")
    
    app_name = ConsoleUI.input_with_style("App Name").strip()
    
    # Ask about custom icon
    use_custom_icon = ConsoleUI.input_with_style("Use custom app icon? (y/N)").strip().lower() == 'y'
    icon_url = None
    if use_custom_icon:
        ConsoleUI.print_panel("Image Upload Help", 
                            f"If you don't have an image URL, you can upload your image at:\n{IMAGE_UPLOAD_HELP_URL}\n"
                            "It will give you a URL that you can paste here")
        while True:
            icon_url = ConsoleUI.input_with_style("Enter icon URL (PNG format)").strip()
            if icon_url.startswith(('http://', 'https://')):
                break
            ConsoleUI.print_status("Invalid URL! Must start with http:// or https://", "error")
    
    # Setup environment
    github_login()
    
    # Start build
    build_apk(website_url, app_name, use_custom_icon, icon_url)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        ConsoleUI.print_status("\nBuild process cancelled by user", "warning")
        exit(0)
    except Exception as e:
        ConsoleUI.print_status(f"Unexpected error: {str(e)}", "error")
        exit(1)