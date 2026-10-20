/* EasyHybrid4 CI: minimal <unistd.h> for building pDynamo3 with MSVC.
   PRIMME's only use, gethostname(), comes from primme_gethostname.h. */
#ifndef EASYHYBRID_MSVC_UNISTD_H
#define EASYHYBRID_MSVC_UNISTD_H
#include <io.h>
#include <process.h>
#endif
