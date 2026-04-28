extern int passed_verification;

int workload_verify(void) {
    return passed_verification != 0;
}
