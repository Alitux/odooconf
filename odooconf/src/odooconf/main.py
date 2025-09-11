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
                    console.log(f":heavy_plus_sign: Nueva carpeta de addons añadida: [green]{parent_dir}[/]")
                    if self.odoo_conf_path:
                        update_paths_odoo_conf(
                            self.odoo_conf_path, ",".join(self.parent_paths)
                        )
                        console.log(f":floppy_disk: Archivo [yellow]{self.odoo_conf_path}[/] actualizado.")

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
        console.print(f":mag: Monitoreando cambios en [bold]{path}[/]...")
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
        console.print("[red]Watchdog detenido.[/]")


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
        err_console.print(f"[bold red]✖ No se encontró el archivo odoo.conf en: {odoo_conf_path}[/]")
        raise typer.Exit(1)

    config = configparser.ConfigParser()
    files_read = config.read(odoo_conf_path)
    if not files_read:
        err_console.print(f"[bold red]✖ No se pudo leer el archivo: {odoo_conf_path}[/]")
        raise typer.Exit(1)
    if "options" not in config:
        err_console.print(f"[bold red]✖ La sección [options] no fue encontrada en el archivo odoo.conf[/]")
        raise typer.Exit(1)

    addons_path_actual = config["options"].get("addons_path", "")
    rutas_actuales = set(addons_path_actual.split(",")) if addons_path_actual else set()
    rutas_actuales.update(new_paths.split(","))

    config["options"]["addons_path"] = ",".join(sorted(rutas_actuales))
    with open(odoo_conf_path, "w") as configfile:
        config.write(configfile)

    console.print(f":white_check_mark: [green]odoo.conf actualizado correctamente.[/]")


def resolver_ruta_odoo_conf(entrada: Optional[str]) -> Optional[str]:
    if not entrada:
        return None

    if os.path.isdir(entrada):
        posible_ruta = os.path.join(entrada, "odoo.conf")
        if os.path.exists(posible_ruta):
            return posible_ruta
        err_console.print(f"[bold red]✖ No se encontró 'odoo.conf' en el directorio: {entrada}[/]")
        raise typer.Exit(1)

    elif os.path.isfile(entrada):
        return entrada

    err_console.print(f"[bold red]✖ La ruta proporcionada no es válida: {entrada}[/]")
    raise typer.Exit(1)

def estimate_workers(users: int = None) -> int:
    """
    Estima el número de workers a partir de la cantidad de usuarios
    """ 
    max_workers = (2 + psutil.cpu_count()) + 1
    workers = max((int(users) // 6) + 1, 1)
    console.print(f":gear: [green]Para [bold]{users}[/bold] usuarios se necesitan [bold]{workers}[/bold] workers[/]")
    if workers > max_workers:
        console.print(f"[bold yellow]✖ El número de workers no puede ser mayor a {max_workers}[/]")
        console.print(f"[bold green]✔ Se redefine el valor de workers a {max_workers}[/]")
        workers = max_workers
    if not users:
        workers = 2
    if workers == 1: 
        workers = 2
    return workers

def generate_admin_passwd_hash(password:str) -> str:
    """Genera un hash de contraseña para el usuario admin."""
    pwd_context = CryptContext(schemes=["pbkdf2_sha512"], deprecated="auto")
    return pwd_context.hash(password)

@app.command()
def new(
    odoo_conf: str = typer.Argument(...,help="Ruta donde se generará el nuevo odoo.conf"),
    users: Optional[int] = typer.Option(None, help="Cantidad de usuarios concurrentes esperados"),
    ):

    """Genera un nuevo archivo odoo.conf con configuraciones base"""
    
    ruta = os.path.join(odoo_conf, "odoo.conf")
    if os.path.exists(ruta):
        err_console.print((f"[bold red]✖ El archivo ya existe: {ruta}[/]"))
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
    with open(ruta, "w") as f:
        config.write(f)
    console.print(f":sparkles: Archivo [yellow]{ruta}[/yellow] generado correctamente con configuración base.")
    console.print(f":bulb: [green] Para optimizar ver las opciones disponibles con:[/] [magenta]odooconf server --help[/]")

@app.command()
def paths(
    base_addons_dir: str = typer.Argument(..., help="Ruta base de los addons"),
    internal_path: str = typer.Option(None, "--internal-path", help="Ruta base interna (Ideal para docker)"), 
    watchdog: bool = typer.Option(False, "--watchdog", help="Activar watchdog para odoo.conf dinámico"),
    odoo_conf: Optional[str] = typer.Option(None, "--odoo-conf", help="Ruta del archivo o carpeta que contiene odoo.conf"),
):
    """
    Busca rutas de addons en Odoo y puede actualizar el odoo.conf dinámicamente si se activa --watchdog.
    """
    odoo_conf_ruta = resolver_ruta_odoo_conf(odoo_conf) if odoo_conf else None
    paths = find_addons_paths(base_addons_dir, internal_base_path=internal_path, list_format=True)
    if internal_path:
        console.print(f":open_file_folder: [cyan]Ruta interna[/cyan] [yellow]{internal_path}[/yellow] como base para paths")
    if watchdog:
        monitoring_path(base_addons_dir, paths, odoo_conf_ruta)
    else:
        addons_str = ",".join(sorted(paths))
        if odoo_conf_ruta:
            update_paths_odoo_conf(odoo_conf_ruta, addons_str)
            console.print(f":floppy_disk: [green]Archivo [yellow]{odoo_conf_ruta}[/yellow] actualizado.[/green]")
        console.print(f"[green]{addons_str}[/green]")

@app.command()
def server(
    odoo_conf: str = typer.Argument(..., help="Ruta al archivo odoo.conf"),
    users: Optional[int] = typer.Option(None, help="Cantidad de usuarios concurrentes esperados"),
    ram: Optional[int] = typer.Option(None, help="RAM total del servidor en GB (opcional)"),
    auto_ram: Optional[bool] = typer.Option(False, help="Calcular automáticamente el valor de RAM"),
    hide_db: Optional[bool] = typer.Option(False, help="Ocultar lista base de datos"),
    time_cpu: Optional[int] = typer.Option(None, help="Tiempo máximo en segundos de CPU que una petición puede consumir"),
    time_real: Optional[int] = typer.Option(None, help="Tiempo máximo en tiempo real (wall time) que una petición puede durar"),
    admin_passwd: Optional[str] = typer.Option(None, help="Contraseña plana para el usuario admin"),
    db_host: Optional[str] = typer.Option(None, help="Host del servidor de base de datos"),
    db_port: Optional[int] = typer.Option(None, help="Puerto del servidor de base de datos"), 
    db_user: Optional[str] = typer.Option(None, help="Usuario del servidor de base de datos"),
    db_password: Optional[str] = typer.Option(None, help="Contraseña del servidor de base de datos"),

):
    """
    Calcula y actualiza automáticamente los workers y límites de memoria en odoo.conf
    según la cantidad de usuarios y memoria disponible.
    """
    path = resolver_ruta_odoo_conf(odoo_conf)
    config = configparser.ConfigParser()
    config.read(path)

    if "options" not in config:
        err_console.print("[bold red]✖ La sección [options] no fue encontrada en odoo.conf[/]")
        raise typer.Exit(1)
    if users: 
        workers = estimate_workers(users)
    if not users:
        workers = 2

    config["options"]["workers"] = str(workers)
    config["options"]["max_cron_threads"] = "1"  # valor recomendado
    
    console.print(f":rocket: [green]{workers} workers[/] establecidos en [yellow]{path}[/yellow]")

    if admin_passwd:
        password = str(generate_admin_passwd_hash(admin_passwd))
        config["options"]["admin_passwd"] = password
        console.print(f":lock: [green]Hash generado:[/] [cyan]{password}[/]")

    if hide_db:
        config["options"]["list_db"] = "False"
        console.print(f":lock: [green]Lista base de datos ocultada.[/]")

    if time_cpu:
        config["options"]["limit_time_cpu"] = str(time_cpu)
        console.print(f":clock3: limit_time_cpu: [cyan]{time_cpu} segundos[/]")

    if time_real:
        config["options"]["limit_time_real"] = str(time_real)
        console.print(f":hourglass: limit_time_real: [cyan]{time_real} segundos[/]")

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
        console.print(f":key: db_password: [red]********[/] (oculto)")

    if ram or auto_ram:
        ram = psutil.virtual_memory().total if auto_ram else ram*1024**3

        limit_soft = int((ram * 0.75) / workers)
        limit_hard = int((ram * 0.95) / workers)

        config["options"]["limit_memory_soft"] = str(limit_soft)
        config["options"]["limit_memory_hard"] = str(limit_hard)
        
        #Solo para consola
        limit_soft_gb = round((limit_soft / 1024 ** 2), 2)
        limit_hard_gb = round((limit_hard / 1024 ** 2), 2)
        
        console.print(f":gear: RAM total: [cyan]{round((ram/1024**3),2)} GB[/] => [green]{workers} workers[/]")
        console.print(f":gear: limit_memory_soft: [yellow]{limit_soft_gb} MB[/], limit_memory_hard: [yellow]{limit_hard_gb} MB[/]")
    with open(path, "w") as f:
        config.write(f)

if __name__ == "__main__":
    app()