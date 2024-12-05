/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The author of this file is Menal Guzelsoy                                 */
/*                                                                           */
/* (c) Copyright 2005-2019 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifdef USE_OSI_INTERFACE

#include "OsiSymSolverInterface.hpp"

int main(int argc, char **argv)
{

  OsiSymSolverInterface si;
  si.parseCommandLine(argc, argv);
  si.loadProblem();
  si.setSymParam(OsiSymKeepWarmStart, true);
  si.setSymParam(OsiSymFindFirstFeasible, true);
   /* set node selection rule to DEPTH_FIRST_SEARCH */
  si.setSymParam(OsiSymSearchStrategy, 3);

  si.initialSolve();

  si.setSymParam(OsiSymFindFirstFeasible, false);
   /* set node selection rule to BEST_FIRST_SEARCH */
  si.setSymParam(OsiSymSearchStrategy, 4);

  si.resolve();
  
  return(0);

}

#else

#include "symphony.h"
  
int main(int argc, char **argv)
{    
     
   sym_environment *env = sym_open_environment();   
   sym_parse_command_line(env, argc, argv);   
   sym_load_problem(env);
   
   sym_set_int_param(env, "keep_warm_start", true);
   sym_set_int_param(env, "find_first_feasible", true);

   /* set node selection rule to DEPTH_FIRST_SEARCH */
   sym_set_int_param(env, "node_selection_rule", 3);

   sym_solve(env);

   sym_set_int_param(env, "find_first_feasible", true);
   /* set node selection rule to BEST_FIRST_SEARCH */
   sym_set_int_param(env, "node_selection_rule", 4);


   sym_warm_solve(env);
   sym_close_environment(env);
  
   return(0);

}  

#endif

