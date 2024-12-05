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
#include <iostream>

int main(int argc, char **argv)
{

  OsiSymSolverInterface si;
  CoinWarmStart *ws;

  si.parseCommandLine(argc, argv);
  si.loadProblem();

  si.setSymParam(OsiSymKeepWarmStart, true);
  si.setSymParam(OsiSymNodeLimit, 100);

  si.initialSolve();
  ws = si.getWarmStart();
  si.setSymParam(OsiSymNodeLimit, 1000);

  si.resolve();

  si.setObjCoeff(0, 1);
  si.setObjCoeff(200, 150);
  si.setWarmStart(ws);

  si.resolve();

  return(0);

}

#else

#include "symphony.h"
  
int main(int argc, char **argv)
{    
     
   sym_environment *env = sym_open_environment();   
   warm_start_desc * ws; 

   sym_parse_command_line(env, argc, argv);   
   sym_load_problem(env);

   sym_set_int_param(env, "keep_warm_start", TRUE);
   sym_set_int_param(env, "node_limit", -1);
   sym_set_int_param(env, "do_reduced_cost_fixing", 0);
   sym_solve(env);
   ws = sym_get_warm_start(env, true);

   sym_set_int_param(env, "node_limit", 1000);

   sym_warm_solve(env);

   sym_set_obj_coeff(env, 0, 1);
   sym_set_obj_coeff(env, 200, 150);

   sym_set_warm_start(env, ws);
   sym_warm_solve(env);

   sym_close_environment(env);
  
   return(0);

}  

#endif

