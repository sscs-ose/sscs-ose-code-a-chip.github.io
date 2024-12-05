/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* (c) Copyright 2000-2019 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef COMPILE_IN_TM

#define COMPILING_FOR_TM

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sym_tm.h"
#include "sym_proccomm.h"
#include "sym_timemeas.h"

/*===========================================================================*/

/*===========================================================================*\
 * This is the main() that is used if the TM is running as a separate        
 * process. This file is only used in that case.                             
\*===========================================================================*/

int main(void)
{
   tm_prob *tm;
   int termcode;
   
   /* set stdout to be line buffered */
   setvbuf(stdout, (char *)NULL, _IOLBF, 0);
   
   register_process();  /*Enroll this program in PVM*/

   tm = (tm_prob *) calloc(1, sizeof(tm_prob));
   
   if ((termcode = tm_initialize(tm, NULL, NULL)) == 0){
      
      tm->start_time = wall_clock(NULL);
   
      termcode = tm_close(tm, solve(tm));
   }

   comm_exit();

   exit(termcode);
}

#endif
