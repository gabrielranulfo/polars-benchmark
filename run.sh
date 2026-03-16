export RUN_LOG_TIMINGS=1
export SCALE_FACTOR=${SCALE_FACTOR:-1}

comando=${comando:-"make run-all"}

#make tables SCALE_FACTOR=$SCALE_FACTOR

eval "$comando"

#make plot