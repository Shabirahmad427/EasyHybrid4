/* EasyHybrid4 CI: minimal <sys/resource.h> for building pDynamo3 with
   MinGW, which has <sys/time.h> but no getrusage(). Used only by PRIMME's
   CPU timer (cprimme/wtime.c); reports process CPU time from clock(). */
#ifndef EASYHYBRID_MINGW_SYS_RESOURCE_H
#define EASYHYBRID_MINGW_SYS_RESOURCE_H
#include <time.h>
#include <sys/time.h>
#define RUSAGE_SELF 0
struct rusage { struct timeval ru_utime; struct timeval ru_stime; };
static __inline int getrusage(int who, struct rusage *usage)
{
    clock_t ticks = clock();
    (void) who;
    usage->ru_utime.tv_sec  = (long) (ticks / CLOCKS_PER_SEC);
    usage->ru_utime.tv_usec = (long) ((ticks % CLOCKS_PER_SEC) * 1000000 / CLOCKS_PER_SEC);
    usage->ru_stime.tv_sec  = 0;
    usage->ru_stime.tv_usec = 0;
    return 0;
}
#endif
