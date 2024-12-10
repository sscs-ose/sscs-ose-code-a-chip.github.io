#include <memory.h>
#include <stdlib.h>

#include "sym_lp_solver.h"
#include "decomp_sym_lp.h"
#include "sym_macros.h"

#if defined(__CPLEX70__) || defined(__CPLEX66__) || defined(__CPLEX65__) || defined(__CPLEX60__) || defined(__CPLEX50__) || defined(__CPLEX40__)

/*****************************************************************************/
/*****************************************************************************/
/*******                                                               *******/
/*******                  routines when CPLEX is used                  *******/
/*******                                                               *******/
/*****************************************************************************/
/*****************************************************************************/

void load_decomp_lp(LPdata *lp_data)
{
   int i, cpx_status, itlim;
   
   lp_data->matcnt = (int *) calloc(lp_data->maxn, sizeof(int));

   for (i=lp_data->n-1; i>=0; i--)
      lp_data->matcnt[i] = lp_data->matbeg[i+1] - lp_data->matbeg[i];

   /*no scaling*/
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_SCAIND, -1);
   
   /* essentially disable basis snapshots */
   cpx_status =
      CPXsetintparam(lp_data->cpxenv, CPX_PARAM_BASINTERVAL, 2100000000);
   CPX_check_error("load_lp - CPXsetintparam");
   lp_data->lp =
      CPXloadlp(lp_data->cpxenv,
		(char *) "Decomp_prob", lp_data->n, lp_data->m, 1,
		lp_data->obj,
		lp_data->rhs, lp_data->sense, lp_data->matbeg, lp_data->matcnt,
		lp_data->matind, lp_data->matval, lp_data->lb, lp_data->ub,
		lp_data->rngval, lp_data->maxn+lp_data->maxm, lp_data->maxm,
		lp_data->maxnz+lp_data->maxm);
   cpx_status = CPXgetintparam(lp_data->cpxenv, CPX_PARAM_ITLIM, &itlim);
   CPX_check_error("load_lp - CPXgetintparam");
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_ITLIM, 0);
   CPX_check_error("load_lp - CPXsetintparam");
   cpx_status = CPXdualopt(lp_data->cpxenv, lp_data->lp);
   CPX_check_error("load_lp - CPXdualopt");
   cpx_status = CPXsetintparam(lp_data->cpxenv, CPX_PARAM_ITLIM, itlim);
   CPX_check_error("load_lp - CPXsetintparam");
   /*Not sure if I need to do this anymore*/
#if 0
   lp_data->lpbas.cstat = (int *) malloc(lp_data->maxn * ISIZE);
   lp_data->lpbas.rstat = (int *) malloc(lp_data->maxm * ISIZE);
#endif
}

void unload_decomp_lp(LPdata *lp_data)
{
   CPXfreeprob(lp_data->cpxenv, &(lp_data->lp));
   
   FREE(lp_data->matcnt);
   /*Uncomment this if I start allocating these again*/
#if 0
   FREE(lp_data->lpbas.cstat);
   FREE(lp_data->lpbas.rstat);
#endif
}   


#elif defined (__XMP__)

/*****************************************************************************/
/*****************************************************************************/
/*******                                                               *******/
/*******                   routines when XMP is used                   *******/
/*******                                                               *******/
/*****************************************************************************/
/*****************************************************************************/

#else /* lpsolve */

/*****************************************************************************/
/*****************************************************************************/
/*******                                                               *******/
/*******                 routines when LPSOLVE is used                 *******/
/*******                                                               *******/
/*****************************************************************************/
/*****************************************************************************/

#endif
