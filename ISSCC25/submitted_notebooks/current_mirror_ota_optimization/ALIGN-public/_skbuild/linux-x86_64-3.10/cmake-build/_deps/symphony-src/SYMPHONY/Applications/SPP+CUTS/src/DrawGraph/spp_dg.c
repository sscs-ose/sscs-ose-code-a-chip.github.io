/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Set Partitioning Problem.                                             */
/*                                                                           */
/* (c) Copyright 2005-2007 Marta Eso and Ted Ralphs. All Rights Reserved.    */
/*                                                                           */
/* This application was originally developed by Marta Eso and was modified   */
/* Ted Ralphs (ted@lehigh.edu)                                               */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdlib.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_dg.h"
#include "sym_dg_u.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the drawgraph process.
\*===========================================================================*/

int user_dg_process_message(void *user, window *win, FILE *write_to)
{
   return(USER_NO_PP);
}

/*===========================================================================*/

int user_dg_init_window(void **user, window *win)
{
   *user = NULL;

   return(USER_NO_PP);
}

/*===========================================================================*/

int user_dg_free_window(void **user, window *win)
{
   FREE(*user);

   return(USER_NO_PP);
}

/*===========================================================================*/

int user_initialize_dg(void **user)
{
   return(USER_NO_PP);
}

/*===========================================================================*/

int user_free_dg(void **user)
{
   return(USER_NO_PP);
}

/*===========================================================================*/

int user_interpret_text(void *user, int text_length, char *text,
			 int owner_tid)
{
   return(USER_NO_PP);
}
