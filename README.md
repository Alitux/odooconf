# OdooConf Tool

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-GPLv2-green.svg)

Herramienta CLI para gestión y optimización de configuraciones de Odoo (`odoo.conf`).

## 📦 Instalación

### Opción 1: Instalación con pip
```bash
pip install git+https://gitlab.com/alitux/odooconf.git
```

### Opción 2: Instalación con pipx (recomendado para aislamiento)
```bash
pipx install git+https://gitlab.com/alitux/odooconf.git
```
### 🔧 Características principales

- 🛠 Generación de configuraciones base optimizadas
- 🔍 Detección automática de rutas de addons
- 👁 Monitoreo en tiempo real con watchdog
- ⚡ Optimización automática de parámetros del servidor
- 🔒 Gestión segura de credenciales

## 🚀 Uso básico

### Generar configuración inicial
```bash
odooconf new /ruta/destino
```
- users: Cantidad de usuarios concurrentes que se espera que el servidor tenga (por defecto: 2)

### Buscar addons y actualizar rutas

```bash
odooconf paths /ruta/addons --odoo-conf /ruta/odoo.conf --internal-path /mnt/odoo/addons
```

- /ruta/addons: Ruta en el sistema de archivos donde se buscarán los addons (host).

- --odoo-conf: Ruta del archivo o carpeta que contiene el odoo.conf que se va a actualizar.

- --internal-path: (Opcional) Ruta interna que se usará en lugar de la ruta del host al escribir en el odoo.conf. Ideal para entornos con contenedores (por ejemplo, Docker).

### Optimizar servidor para 50 usuarios

```bash
odooconf server /ruta/odoo.conf --users 50 --auto-ram
```

## 🔧 Configuración Avanzada del Servidor (`server`)

El comando `server` optimiza automáticamente los parámetros de rendimiento en `odoo.conf`:

### 🖥️ Parámetros de Hardware
```bash
--users N       # Calcula workers: (users/6) + 1 (requerido para cálculo automático)
--ram X         # RAM total en GB (ej: --ram 8 para 8GB)
--auto-ram      # Detecta RAM automáticamente (anula --ram si está presente)
```
## ⏱️ Límites de Tiempo
```bash
--time-cpu N    # Límite de CPU por petición (default: 60s)
--time-real N   # Tiempo real máximo por petición (default: 120s)
```
## 🔐 Configuración de Base de Datos
```bash
--db-host HOST  # Host de PostgreSQL (default: db)
--db-port PORT  # Puerto (default: 5432)  
--db-user USER  # Usuario (default: odoo)
--db-pass PASS  # Contraseña (default: odoo)
--hide-db       # Ocultar la lista de bases de datos (web/database/selector)
```
## 🔄 Valores Automáticos
Con --auto-ram o --ram se calculan:

- limit_memory_soft: 75% RAM/worker
- limit_memory_hard: 95% RAM/worker
- workers: Basado en --users (default: 2)

## 🔒 Seguridad
Se puede generar la contraseña de administrador con:
```bash
--admin-passwd PASS  # Genera hash PBKDF2 (no almacena texto plano)
```
## 💻 Ejemplo Completo
```bash
odooconf server /etc/odoo.conf \
  --users 100 \
  --auto-ram \
  --time-cpu 90 \
  --time-real 180 \
  --admin-passwd "S3cr3tP@ss" \
  --db-host db-prod \
  --db-port 5433
```

## 📄 Licencia

## Este proyecto está licenciado bajo GNU GPLv2.

## 🌍 Repositorio

https://gitlab.com/alitux/odooconf

## 🤝 Contribuciones

Se aceptan contribuciones vía merge requests en el repositorio GitLab.

## 💡 Soporte

Reportar issues en: https://gitlab.com/alitux/odooconf/-/issues