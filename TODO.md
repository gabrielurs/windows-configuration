# Pendiente

## Probar una instalación limpia en otra máquina (PC de casa)

Apuntado el 16 de noviembre de 2026. En la máquina de trabajo no se hizo a propósito:
desmontar el escritorio en mitad de la jornada no compensaba.

**Qué está probado y qué no.** La instalación automática de los mods de Windhawk
(`lib/mods.py`) se probó con UN mod: se quitó `explorer-force-details-columns` y el
instalador lo repuso solo, con la huella correcta y cargado en explorer. Los trece mods se
compararon byte a byte con los que sirve `mods.windhawk.net`. Lo que nadie ha visto todavía
es el instalador entero sobre una máquina que no conoce este repo.

### Antes de empezar

- [ ] Que el commit con `lib/mods.py` esté **subido** a GitHub: `bootstrap.sh` baja `main`,
      y sin push el otro PC instala la versión de antes, la del paso manual.
- [ ] Windows 11 con WSL2 y una distro Ubuntu. Los mods y sus huellas están fijados para
      la build 26200 y Windhawk 1.7.3; con otra build puede que algún selector no pinte.

### La prueba

```bash
curl -fsSL https://raw.githubusercontent.com/gabrielurs/windows-configuration/main/bootstrap.sh | bash
# o, con el repo ya clonado:
./install.sh --dry-run     # primero, para ver qué haría
./install.sh
```

Avisos de UAC esperados: uno para instalar los mods y otro para sus ajustes (más los de
winget si faltan Windhawk, Flow Launcher o AutoHotkey).

### Qué mirar

- [ ] **Los trece mods se instalan solos**, sin abrir Windhawk. El instalador dice
      «faltan 13 de 13», los baja, comprueba huellas y acaba con «instalados: …». Si alguno
      queda fuera, lo lista con su nombre y su URL.
- [ ] **Windhawk recién instalado y nunca abierto.** Es el caso que aquí no se pudo probar:
      los mods necesitan a su lado `libc++.whl`, `libunwind.whl` y `windhawk-mod-shim.dll`,
      que la interfaz de Windhawk copia al arrancar. `lib/mods.py` las pone si faltan; hay
      que ver que los mods cargan de verdad (la barra cambia) sin haber abierto Windhawk.
- [ ] La barra queda a 36 px, con hora y fecha en una línea y `cpu · ram · rama` a la
      izquierda. Si la bandeja sale descentrada, es `taskbar.trayOffset` (7 px medidos en
      una pantalla de 1920×1080 al 100 %; con otra escala habrá que volver a medirlo).
- [ ] El Explorador abre sin barra de comandos y sin hueco en blanco.
- [ ] Una pestaña nueva de Windows Terminal abre Ubuntu, entra sola en tmux y enseña su
      carpeta en el título.
- [ ] El puntero queda oscuro (el instalador abre Configuración unos segundos para ello).
- [ ] `./install.sh --self-test` — aquí da 109/110; el que falla, `cdpath y ~p`, es de esta
      máquina y allí puede pasar.

### Y la vuelta

- [ ] `./install.sh --uninstall` devuelve la máquina a como estaba, mods incluidos (sus
      claves se borran; las DLL se quedan en `%ProgramData%\Windhawk\Engine\Mods`, huérfanas
      e inofensivas — quitarlas pide otro paso elevado que no está escrito).

### Si algo falla

- Un reinicio del shell de Windows al importar ajustes de Windhawk se vio tres veces de
  seis en la máquina de trabajo. Recarga la barra y cierra las ventanas del Explorador; no
  pierde nada más. Causa sin identificar (ver HANDOFF).
- Huella que no coincide: el servidor sirve otra cosa que la que se probó. No forzarlo;
  mirar si el mod se actualizó y, si es así, `python3 lib/mods.py pin` tras probarlo.
