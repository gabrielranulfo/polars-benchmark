export RUN_LOG_TIMINGS=1
export SCALE_FACTOR=${SCALE_FACTOR:-1}

make tables SCALE_FACTOR=$SCALE_FACTOR

make run-all

#make plot