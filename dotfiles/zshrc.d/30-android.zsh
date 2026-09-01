# SDK de Android. Todo condicionado a que los directorios existan, para que en
# una máquina sin Android esto no ensucie el PATH ni dé errores.
_ctt_android="${ANDROID_HOME:-$HOME/Android/Sdk}"
_ctt_jdk="${JAVA_HOME:-$HOME/Android/jdk}"

if [[ -d $_ctt_android ]]; then
  export ANDROID_HOME="$_ctt_android"
  export ANDROID_SDK_ROOT="$ANDROID_HOME"
  [[ -d $ANDROID_HOME/platform-tools ]] && path=($ANDROID_HOME/platform-tools $path)
  [[ -d $ANDROID_HOME/emulator ]]       && path=($ANDROID_HOME/emulator $path)
fi
if [[ -d $_ctt_jdk ]]; then
  export JAVA_HOME="$_ctt_jdk"
  [[ -d $JAVA_HOME/bin ]] && path=($JAVA_HOME/bin $path)
fi
unset _ctt_android _ctt_jdk
export PATH
