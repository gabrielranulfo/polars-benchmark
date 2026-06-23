export RUN_LOG_TIMINGS=1
export SCALE_FACTOR=${SCALE_FACTOR:-1}

# Prioridade: comando > RUN_LIBRARIES > make run-all
if [ -n "${comando+set}" ]; then
    eval "$comando"
elif [ -n "$RUN_LIBRARIES" ]; then
    IFS=',' read -ra LIBS <<< "$RUN_LIBRARIES"
    for lib in "${LIBS[@]}"; do
        lib=$(echo "$lib" | xargs)
        echo "=== Executando $lib ==="
        make "run-$lib"
    done
else
    make run-all
fi