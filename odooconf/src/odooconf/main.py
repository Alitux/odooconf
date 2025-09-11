import configparser
import logging
import os
import psutil
import typer
from passlib.context import CryptContext
from rich import print as rprint
from rich.console import Console
from rich.markup import escape
from typing import Optional, Set
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

app = typer.Typer()
console = Console()
err_console = Console(stderr=True)


class LoggingEventHandler(FileSystemEventHandler):
    def __init__(self, parent_paths: Set[str], odoo_conf_path: Optional[str] = None):
        super().__init__()
        self.parent_paths = parent_paths
        self.odoo_conf_path = odoo_conf_path

    def on_created(self, event):
        if event.is_directory:
            if self.is_addon_directory(event.src_path):
                parent_dir = os.path.abspath(os.path.dirname(event.src_path))
                if parent_dir not in self.parent_paths:
                    self.parent_paths.add(parent_dir)
                    console.log(f":heavy_plus_sign: New addons folder added: [green]{parent_dir}[/]")
                    if self.odoo_conf_path:
                        update_paths_odoo_conf(
                            self.odoo_conf_path, ",".join(self.parent_paths)
                        )
                        console.log(f":floppy_disk: File [yellow]{self.odoo_conf_path}[/] updated.")

    def is_addon_directory(self, directory):
        return "__manifest__.py" in os.listdir(directory)


def monitoring_path(path: str, parent_paths: Set[str], odoo_conf_path: Optional[str] = None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    event_handler = LoggingEventHandler(parent_paths, odoo_conf_path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        console.print(f":mag: Monitoring changes in [bold]{path}[/]...")
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
        console.print("[red]Watchdog stopped.[/]")


def find_addons_paths(base_path: str, internal_base_path: str = None, list_format: bool = False):
    parent_paths = set()
    for root, dirs, files in os.walk(base_path):
        if "__manifest__.py" in files:
            parent_dir = os.path.abspath(os.path.dirname(root))
            if internal_base_path:
                relative_path = os.path.relpath(parent_dir, base_path)
                new_path = os.path.join(internal_base_path, relative_path)
                parent_paths.add(new_path)
            else:
                parent_paths.add(parent_dir)
    return parent_paths if list_format else ",".join(parent_paths)


def update_paths_odoo_conf(odoo_conf_path: str, new_paths: str):
    if not os.path.exists(odoo_conf_path):
        err_console.print(f"[bold red]✖ odoo.conf file not found at: {odoo_conf_path}[/]")
        raise typer.Exit(1)

    config = configparser.ConfigParser()
    files_read = config.read(odoo_conf_path)
    if not files_read:
        err_console.print(f"[bold red]✖ Could not read file: {odoo_conf_path}[/]")
        raise typer.Exit(1)
    if "options" not in config:
        err_console.print(f"[bold red]✖ [options] section not found in odoo.conf file[/]")
        raise typer.Exit(1)

    current_addons_path = config["options"].get("addons_path", "")
    current_paths = set(current_addons_path.split(",")) if current_addons_path else set()
    current_paths.update(new_paths.split(","))

    config["options"]["addons_path"] = ",".join(sorted(current_paths))
    with open(odoo_conf_path, "w") as configfile:
        config.write(configfile)

    console.print(f":white_check_mark: [green]odoo.conf updated successfully.[/]")


def resolve_odoo_conf_path(entry: Optional[str]) -> Optional[str]:
    if not entry:
        return None

    if os.path.isdir(entry):
        possible_path = os.path.join(entry, "odoo.conf")
        if os.path.exists(possible_path):
            return possible_path
        err_console.print(f"[bold red]✖ 'odoo.conf' not found in directory: {entry}[/]")
        raise typer.Exit(1)

    elif os.path.isfile(entry):
        return entry

    err_console.print(f"[bold red]✖ The provided path is not valid: {entry}[/]")
    raise typer.Exit(1)

def estimate_workers(users: int = None) -> int:
    """
    Estimates the number of workers based on the number of users
    """ 
    max_workers = (2 + psutil.cpu_count()) + 1
    workers = max((int(users) // 6) + 1, 1)
    console.print(f":gear: [green]For [bold]{users}[/bold] users, [bold]{workers}[/bold] workers are needed[/]")
    if workers > max_workers:
        console.print(f"[bold yellow]✖ The number of workers cannot be greater than {max_workers}[/]")
        console.print(f"[bold green]✔ The value of workers is redefined to {max_workers}[/]")
        workers = max_workers
    if not users:
        workers = 2
    if workers == 1: 
        workers = 2
    return workers


def generate_admin_passwd_hash(password:str) -> str:
    """Generates a password hash for the admin user."""
    pwd_context = CryptContext(schemes=["pbkdf2_sha512"], deprecated="auto")
    return pwd_context.hash(password)

@app.command()
def new(
    odoo_conf: str = typer.Argument(...,help="Path where the new odoo.conf will be generated"),
    users: Optional[int] = typer.Option(None, help="Number of expected concurrent users"),
    ):

    """Generates a new odoo.conf file with base configurations"""
    
    path = os.path.join(odoo_conf, "odoo.conf")
    if os.path.exists(path):
        err_console.print(f"[bold red]✖ File already exists: {path}[/]")
        raise typer.Exit(1)
    config = configparser.ConfigParser()
    config["options"] = {
        "addons_path": "/mnt/extra-addons",
        # "admin_passwd": generate_admin_passwd_hash("admin"),
        "db_host": "db",
        "db_port": "5432",
        "db_user": "odoo",
        "db_password": "odoo",
        "workers": str(estimate_workers(users)) if users else "2",
        "limit_time_cpu":"60",
        "limit_time_real":"120",
    }

    os.makedirs(odoo_conf, exist_ok=True)
    with open(path, "w") as f:
        config.write(f)
    console.print(f":sparkles: File [yellow]{path}[/yellow] generated successfully with base configuration.")
    console.print(f":bulb: [green] To optimize, see the available options with:[/] [magenta]odooconf server --help[/]")

@app.command()
def paths(
    base_addons_dir: str = typer.Argument(..., help="Base path for addons"),
    internal_path: str = typer.Option(None, "--internal-path", help="Internal base path (Ideal for docker)"), 
    watchdog: bool = typer.Option(False, "--watchdog", help="Activate watchdog for dynamic odoo.conf"),
    odoo_conf: Optional[str] = typer.Option(None, "--odoo-conf", help="Path to the file or folder containing odoo.conf"),
):
    """
    Searches for Odoo addon paths and can dynamically update odoo.conf if --watchdog is activated.
    """
    odoo_conf_path = resolve_odoo_conf_path(odoo_conf) if odoo_conf else None
    paths = find_addons_paths(base_addons_dir, internal_base_path=internal_path, list_format=True)
    if internal_path:
        console.print(f":open_file_folder: [cyan]Internal path[/cyan] [yellow]{internal_path}[/yellow] as base for paths")
    if watchdog:
        monitoring_path(base_addons_dir, paths, odoo_conf_path)
    else:
        addons_str = ",".join(sorted(paths))
        if odoo_conf_path:
            update_paths_odoo_conf(odoo_conf_path, addons_str)
            console.print(f":floppy_disk: [green]File [yellow]{odoo_conf_path}[/yellow] updated.[/green]")
        console.print(f"[green]{addons_str}[/green]")

@app.command()
def server(
    odoo_conf: str = typer.Argument(..., help="Path to the odoo.conf file"),
    users: Optional[int] = typer.Option(None, help="Number of expected concurrent users"),
    ram: Optional[int] = typer.Option(None, help="Total server RAM in GB (optional)"),
    auto_ram: Optional[bool] = typer.Option(False, help="Automatically calculate the RAM value"),
    hide_db: Optional[bool] = typer.Option(False, help="Hide database list"),
    time_cpu: Optional[int] = typer.Option(None, help="Maximum CPU time in seconds that a request can consume"),
    time_real: Optional[int] = typer.Option(None, help="Maximum real time (wall time) that a request can last"),
    admin_passwd: Optional[str] = typer.Option(None, help="Plain password for the admin user"),
    db_host: Optional[str] = typer.Option(None, help="Database server host"),
    db_port: Optional[int] = typer.Option(None, help="Database server port"), 
    db_user: Optional[str] = typer.Option(None, help="Database server user"),
    db_password: Optional[str] = typer.Option(None, help="Database server password"),

):
    """
    Automatically calculates and updates workers and memory limits in odoo.conf
    according to the number of users and available memory.
    """
    path = resolve_odoo_conf_path(odoo_conf)
    config = configparser.ConfigParser()
    config.read(path)

    if "options" not in config:
        err_console.print("[bold red]✖ [options] section not found in odoo.conf[/]")
        raise typer.Exit(1)
    if users: 
        workers = estimate_workers(users)
    if not users:
        workers = 2

    config["options"]["workers"] = str(workers)
    config["options"]["max_cron_threads"] = "1"  # recommended value
    
    console.print(f":rocket: [green]{workers} workers[/] set in [yellow]{path}[/yellow]")

    if admin_passwd:
        password = str(generate_admin_passwd_hash(admin_passwd))
        config["options"]["admin_passwd"] = password
        console.print(f":lock: [green]Hash generated:[/] [cyan]{password}[/]")

    if hide_db:
        config["options"]["list_db"] = "False"
        console.print(f":lock: [green]Database list hidden.[/]")

    if time_cpu:
        config["options"]["limit_time_cpu"] = str(time_cpu)
        console.print(f":clock3: limit_time_cpu: [cyan]{time_cpu} seconds[/]")

    if time_real:
        config["options"]["limit_time_real"] = str(time_real)
        console.print(f":hourglass: limit_time_real: [cyan]{time_real} seconds[/]")

    if db_host:
        config["options"]["db_host"] = db_host
        console.print(f":globe_with_meridians: db_host: [cyan]{db_host}[/]")

    if db_port:
        config["options"]["db_port"] = str(db_port)
        console.print(f":triangular_ruler: db_port: [cyan]{db_port}[/]")

    if db_user:
        config["options"]["db_user"] = db_user
        console.print(f":bust_in_silhouette: db_user: [green]{db_user}[/]")

    if db_password:
        config["options"]["db_password"] = db_password
        console.print(f":key: db_password: [red]********[/] (hidden)")

    if ram or auto_ram:
        ram = psutil.virtual_memory().total if auto_ram else ram*1024**3

        limit_soft = int((ram * 0.75) / workers)
        limit_hard = int((ram * 0.95) / workers)

        config["options"]["limit_memory_soft"] = str(limit_soft)
        config["options"]["limit_memory_hard"] = str(limit_hard)
        
        #For console only
        limit_soft_gb = round((limit_soft / 1024 ** 2), 2)
        limit_hard_gb = round((limit_hard / 1024 ** 2), 2)
        
        console.print(f":gear: Total RAM: [cyan]{round((ram/1024**3),2)} GB[/] => [green]{workers} workers[/]")
        console.print(f":gear: limit_memory_soft: [yellow]{limit_soft_gb} MB[/], limit_memory_hard: [yellow]{limit_hard_gb} MB[/]")
    with open(path, "w") as f:
        config.write(f)

if __name__ == "__main__":
    app()