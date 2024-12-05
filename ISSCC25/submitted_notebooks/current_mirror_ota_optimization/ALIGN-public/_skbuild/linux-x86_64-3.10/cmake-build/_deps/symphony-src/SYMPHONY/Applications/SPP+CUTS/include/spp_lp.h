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

#ifndef _SPP_LP_H_
#define _SPP_LP_H_

#include "sym_proto.h"
#include "sym_types.h"
#include "sym_dg_params.h"
#include "sym_lp.h"

#include "spp_types.h"
#include "spp_lp_params.h"

typedef struct SPP_LP_TMP {
   char               *ctmp_2nD;       /* length: 2*n*DSIZE */
   double             *dtmp_m;         /* length rownum */
   double             *dtmp_n;
   int                *itmp_m;
   int                *itmp_2n;
}spp_lp_tmp;


typedef struct SPP_LP_PROBLEM {
   spp_lp_params      *par;
   spp_lp_tmp         *tmp;
   col_ordered        *cmatrix;
   char                wname[MAX_NAME_LENGTH +1];
                          /* name of window in which frac solns are dispd */
}spp_lp_problem;

#endif
