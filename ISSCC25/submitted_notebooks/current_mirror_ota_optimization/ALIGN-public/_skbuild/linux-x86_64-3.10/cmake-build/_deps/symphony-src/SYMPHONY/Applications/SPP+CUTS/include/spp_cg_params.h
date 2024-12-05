/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2013 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#ifndef _SPP_CG_PARAMS_H
#define _SPP_CG_PARAMS_H

typedef struct SPP_CG_PARAMS{
   double     min_violation_clique;
   double     min_violation_oddhole;
   double     min_violation_oddantihole;
   double     min_violation_wheel;
   double     min_violation_orthocut;
   double     min_violation_othercut;

   int        starcl_degree_threshold; /* star cls below this are enumerated */
   int        starcl_which_node;
   int        rowcl_degree_threshold;  /* same for row cliques */
   int        max_hub_num;        /* max num of hubs when lifting odd holes */
   int        eval_oh_during_lifting; /* T/F eval oh after every lifted hub */
}spp_cg_params;

#endif
