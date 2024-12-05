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

#ifndef _SPP_LP_PARAMS_H
#define _SPP_LP_PARAMS_H

typedef struct SPP_LP_PARAMS{
   double           granularity;      /* inherited from air_params */
   int              do_lift_in_lp;
   double           lp_dj_threshold_frac;
   double           lp_dj_threshold_abs;
   int              lanmax;
   int              which_atilde;
}spp_lp_params;

#endif
