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

#ifndef _SPP_MASTER_FUNCTIONS_H
#define _SPP_MASTER_FUNCTIONS_H

#include "sym_proto.h"

#include "spp.h"

void   spp_read_params       PROTO((spp_problem *spp, char *filename));
void   spp_print_params      PROTO((spp_problem *spp));
void   spp_read_input        PROTO((spp_problem *spp));
void   read_our_no_del       PROTO((col_ordered *matrix, FILE *f));
int    read_our_del_dupl     PROTO((col_ordered *matrix, FILE *f));
void   read_our0_no_del      PROTO((col_ordered *matrix, FILE *f));
int    read_our0_del_dupl    PROTO((col_ordered *matrix, FILE *f));
void   spp_fix_lex           PROTO((spp_problem *spp));
void   spp_matrix_to_our     PROTO((col_ordered *matrix, char *filename,
				    int *counter));
void   spp_matrix_to_matlab  PROTO((col_ordered *matrix, char *filename,
				    int *counter));
#endif
