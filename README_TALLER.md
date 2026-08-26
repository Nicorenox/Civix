# Civix - Desarrollado Entrega 1

# 1. Clonar el repositorio
git clone https://github.com/Nicorenox/Civix
Cd <Carpeta donde se clono>
cd Civix 

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. (Opcional) Crear superusuario para el panel /admin/
python manage.py createsuperuser

# 6. Correr las pruebas (deben pasar las 11)
python manage.py test

###Puede ocurrir que un test falle ya que se hace aleatoriamente y un test es precisamente que la inspeccion se confirme para que el avance sea actualizado, por ende estso terminos se dan aleatorios y pueden fallar dando:

'inspeccion_confirmada' != 'avance_actualizado' 
FAILED (failures=1)

# 7. Levantar el servidor para pruebas graficas
python manage.py runserver

# 8. Probar
# - Admin:          http://127.0.0.1:8000/admin/      (Se recomienda hacer esto primero para verificar que existen empresas)

# - Desde admin:    Crear Empresa -> Crear Suscripción para esa empresa -> crear usuarios

# - Interfaz HTML:  http://127.0.0.1:8000/api/empresas/<empresa_id>/proyectos/crear/ (<empresa_id> requiere de una empresa creada desde admin, se podra ver ingresando a la empresa de admin, en la barra de buscador aparecera algo parecido a: http://127.0.0.1:8000/admin/proyectos/empresa/f090cff2-cd95-43f7-b20d-3e3b9b17db14/change/. Lo que nos importa para llegar a la interfaz es f090cff2-cd95-43f7-b20d-3e3b9b17db14 , este sera nuestro id de empresa )

# - Login:          http://127.0.0.1:8000/api/login/ (Desde aca si se creo anteriormente un usuario como colaborador o administrador se dara un panel diferente en el cual se busca dar diferentes roles donde se podra crear una nueva inspeccion y confrimarla apareciendo en la bitacora)

# - API:            http://127.0.0.1:8000/api/ (Verficar que la API este funcionando)
