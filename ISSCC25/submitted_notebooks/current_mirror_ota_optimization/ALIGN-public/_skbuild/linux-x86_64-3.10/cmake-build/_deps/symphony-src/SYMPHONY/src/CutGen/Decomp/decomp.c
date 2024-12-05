#include <memory.h>
#include <string.h>

#include "decomp.h"
#include "sym_timemeas.h"
#include "sym_messages.h"
#include "decomp_types.h"
#include "sym_proccomm.h"
#include "decomp_sym_lp.h"
#include "sym_constants.h"
#include "sym_macros.h"

#define FARKAS 3

int decomp(cg_prob *p)
{
   LPdata *lp_data = p->dcmp_data.lp_data;
   decomp_data *dcmp_data = &p->dcmp_data;
   int new_cols = -1, i, j, termcode;
   char set_rhs, has_all_cols = FALSE;
   int cpx_status, violation;
   cut_data *new_cut;
   double *binvrow;
   
   set_rhs = user_set_rhs(lp_data->m-1, lp_data->rhs, p->cur_sol.xlength,
			  p->cur_sol.xind, p->cur_sol.xval, p->user);

   if (!set_rhs){
      for (i = 0, j = 0; i < lp_data->m - 1; i++){
	 if (j < p->cur_sol.xlength && p->cur_sol.xind[j] == i)
	    lp_data->rhs[i] = p->cur_sol.xval[j++];
	 else
	    lp_data->rhs[i] = 0;
      }
   }
   lp_data->rhs[lp_data->m-1] = 1;

   dcmp_data->dunbr = 0;
   dcmp_data->iter_num = 0;

   if (!(new_cols = create_initial_lp(p))){
      unload_decomp_lp(p->dcmp_data.lp_data);
      user_free_decomp_data_structures(p, &p->user);
      printf("Performed 0 iterations in decomp\n");
      return(0);
   }

   while (TRUE){
      dcmp_data->iter_num++;
      
      /* solve the current lp*/
      /*Again, this is some LP-solver dependent stuff*/
      termcode = CPXdualopt(lp_data->cpxenv, lp_data->lp);

      switch (CPXgetstat(lp_data->cpxenv,lp_data->lp)){
      case CPX_OPTIMAL:              termcode = OPTIMAL; break;
      case CPX_INFEASIBLE:           termcode = D_INFEASIBLE; break;
      case CPX_UNBOUNDED:            termcode = D_UNBOUNDED; break;
      case CPX_OBJ_LIM:              termcode = D_OBJLIM; break;
      case CPX_IT_LIM_FEAS:
      case CPX_IT_LIM_INFEAS:        termcode = D_ITLIM; break;
      default:                       termcode = ABANDONED; break;
      }
      
      if (termcode == OPTIMAL || p->par.decomp_complete_enum){
	 if (termcode == D_UNBOUNDED)
	    has_all_cols = TRUE;
	 /*if (termcode != OPTIMAL){
	    if (termcode != D_UNBOUNDED)
	       printf("######## CutGen: Unexpected exit status %i########\n\n",
		      termcode);
	    else if (new_cols < p->par.decomp_max_col_num_per_iter)
	       has_all_cols = TRUE;
	 }*/
	 break;
      }

      violation = get_proof_of_infeas(lp_data, &dcmp_data->dunbr);
      
      get_cols_from_pool(p, p->sol_pool);

      new_cols = generate_new_cols(p);
      
      if (termcode != D_UNBOUNDED)
	 printf("######## CutGen: Unexpected exit status %i########\n\n",
		termcode);
      
      if (dcmp_data->iter_num%p->par.decomp_sol_pool_check_freq == 0 &&
	  p->sol_pool)
	 new_cols += receive_cols(p);
      
      if (new_cols == 0){
	 /*This assumes an exact column generator*/
	 has_all_cols = TRUE;
	 break;
      }
   }

   printf("There are %i columns in the decomp LP at termination\n",
	  lp_data->n);
   if(termcode == OPTIMAL){
      new_cols = generate_cuts(p);
      unload_decomp_lp(p->dcmp_data.lp_data);
      user_free_decomp_data_structures(p, &p->user);
      printf("Decomp imposed %i new constraints\n", new_cols);
      return(new_cols);
   }
   else{
      if (has_all_cols){
	 binvrow = (double *) malloc(lp_data->m*DSIZE);
	 lp_data->slacks = (double *) malloc(lp_data->m*DSIZE);
	 cpx_status = CPXgetslack(lp_data->cpxenv, lp_data->lp,
				  lp_data->slacks, 0, lp_data->m-1);
	 CPX_check_error("get_slacks");
	 violation = get_proof_of_infeas(lp_data, &dcmp_data->dunbr);
	 new_cut = (cut_data *) calloc (1, sizeof(cut_data));
	 cpx_status = CPXgetpi(lp_data->cpxenv, lp_data->lp, binvrow,
			       0, lp_data->m-1);
	 CPX_check_error("get_dualsol");
	 get_binvrow(lp_data, dcmp_data->dunbr, binvrow);
	 new_cut->type = FARKAS;
	 new_cut->rhs = -binvrow[lp_data->m-1];
	 new_cut->size = (lp_data->m-1)*DSIZE;
	 new_cut->coef = (char *)malloc((lp_data->m-1)*DSIZE);
	 memcpy(new_cut->coef, binvrow, (lp_data->m-1)*DSIZE);
	 cg_send_cut(new_cut);
	 free ((char *)new_cut->coef);
	 FREE(new_cut);
	 printf("New Farkas cut added\n");
      } 
      unload_decomp_lp(p->dcmp_data.lp_data);
      user_free_decomp_data_structures(p, &p->user);
      return(0);
   }
}

/*****************************************************************************/
/*****************************************************************************/

int create_initial_lp(cg_prob *p)
{
   dcmp_col_set *cols;
   LPdata *lp_data = p->dcmp_data.lp_data;
   col_data *packed_col = (col_data *) calloc (1, sizeof(col_data));
   int i, j, k, col_count, nzcnt, info, s_bufid, col_nzcnt;
   double etol = p->cur_sol.lpetol;
   char add_col;
   
   get_cols_from_pool(p, p->sol_pool);
   cols = user_generate_new_cols(p);

   /*This is to allow some elements to be added in twice (i.e. the depot edges
     in the VRP*/
   memset(lp_data->matval, 0, (cols->nzcnt+cols->num_cols)*sizeof(double));

   for (i = 0, nzcnt = 0, col_count = 0; i < cols->num_cols; i++){
      for (j = cols->matbeg[i], k = 0, col_nzcnt = 0, add_col = TRUE;
	   j<cols->matbeg[i+1] && k < lp_data->m-1; k++){
	 /*This check is currently screwing things up but it should be added
	   back in in some other form at some point since it does limit the
	   number of columns in the LP*/
	 /*if (lp_data->rhs[k] < etol){
            if (cols->matind[j] == k)
	       break;
	    else
	       continue;
	 }
	 if (lp_data->rhs[k] > 1-etol && cols->matind[j] != k)
	    break;*/
	 if (cols->matind[j] == k){
	    if (lp_data->rhs[k] < etol){
	       nzcnt -= col_nzcnt;
	       add_col = FALSE;
	       break;
	    }
	    /*while (j<cols->matbeg[i+1]){
	       if (!(cols->matind[j] == k)) break;
	       lp_data->matval[nzcnt] += 1;
	       lp_data->matind[nzcnt++] = cols->matind[j++];
	       col_nzcnt++;
	    }*/
	    lp_data->matind[nzcnt] = k;
	    while (j<cols->matbeg[i+1]){
	       if (!(cols->matind[j] == k)) break;
	       lp_data->matval[nzcnt] += 1;
	       j++;
	    }
	    nzcnt++;
	    col_nzcnt++;
	 }
      }
      if (!add_col){
	 add_col = TRUE;	 
	 continue;
      }

      lp_data->matind[nzcnt] = lp_data->m-1;
      lp_data->matval[nzcnt++] = 1;
      lp_data->lb[col_count] = 0;
      lp_data->ub[col_count++] = 1;
      lp_data->matbeg[col_count] = nzcnt;

      if (p->sol_pool){
	 user_pack_col(cols->matind+cols->matbeg[i],
		       cols->matbeg[i+1]-cols->matbeg[i], packed_col);
	 
	 if ((s_bufid = pvm_initsend(PvmDataRaw)) < 0) PVM_ERROR(s_bufid);
	 if ((info = pvm_pkint(&packed_col->size, 1, 1)) < 0) PVM_ERROR(info);
	 if ((info = pvm_pkint(&p->cur_sol.xlevel, 1, 1)) < 0) PVM_ERROR(info);
	 if ((info = pvm_pkbyte(packed_col->coef, packed_col->size, 1)) < 0)
	    PVM_ERROR(info);
	 if ((info = pvm_send(p->sol_pool, PACKED_COL)) < 0) PVM_ERROR(info);
	 if ((info = pvm_freebuf(s_bufid)) < 0) PVM_ERROR(info);
      }

      FREE(packed_col->coef);

      if (col_count > p->par.decomp_max_col_num_per_iter) break;
   }

   lp_data->n = col_count;
   lp_data->nz = nzcnt;

   if (p->sol_pool && col_count < p->par.decomp_max_col_num_per_iter)
      receive_cols(p);

   free_dcmp_col_set(cols);
   FREE(cols);
   FREE(packed_col);

   if (!lp_data->n)
      return(0);

   load_decomp_lp(lp_data);
   
   p->dcmp_data.iter_num = 0;

   return(lp_data->n);
}
   
/*===========================================================================*
 * This function receives the cols to be added to the problem and adds them.
 * First it stores all the cols to be added in the "cols" structure as a col
 * ordered sparse matrix. Then adds them all at once.
 *===========================================================================*/

int receive_cols(cg_prob *p)
{
   int num_cols = 0, r_bufid, bytes, msgtag, sender;
   dcmp_col_set cols;
   int varnum = p->dcmp_data.lp_data->m;
   int sol_id[2];
   char block = TRUE;
   static struct timeval tout = {15, 0};

   /*------------------------------------------------------------------------*
    * set up the data structure to store the cols so that they can all be
    * added at once instead of one at a time -- this more efficient
    *------------------------------------------------------------------------*/
   cols.lb = (double *) calloc (COL_BLOCK_SIZE, sizeof(double));
   cols.ub = (double *) calloc (COL_BLOCK_SIZE, sizeof(double));
   cols.matbeg = (int *) calloc (COL_BLOCK_SIZE+1, sizeof(int));
   cols.matind = (int *) calloc (varnum*COL_BLOCK_SIZE, sizeof(int));
   cols.matval = (double *) calloc (varnum*COL_BLOCK_SIZE, sizeof(double));
   cols.obj = (double *) calloc (COL_BLOCK_SIZE, sizeof(double));
   cols.num_cols = 0;
   cols.max_cols = COL_BLOCK_SIZE;
   cols.nzcnt = 0;
   cols.max_nzcnt = varnum*COL_BLOCK_SIZE;

   /*------------------------------------------------------------------------*
    * if "wait_for_cols" is set, then the we wait for all the cols associated
    * with the current LP solution to come back before we return. Normally,
    * we simply receive all the cols currently in the buffer and then return.
    *------------------------------------------------------------------------*/

   if (p->par.decomp_wait_for_cols){
      while(TRUE){
	 do{
	    PVM_FUNC(r_bufid, pvm_trecv(ANYONE, ANYTHING, &tout));
	    if (! r_bufid){
	       if (pvm_pstat(p->tree_manager) != PvmOk){
		  printf("TM has died -- decomp exiting\n\n");
		  exit(-501);
	       }
	    }
	 }while (! r_bufid);
	 pvm_bufinfo(r_bufid, &bytes, &msgtag, &sender);
	 num_cols += dcmp_process_message(p, sender, msgtag, &cols, sol_id);
	 pvm_freebuf(r_bufid);

	 if (p->par.decomp_max_col_num_per_iter &&
	     num_cols >= p->par.decomp_max_col_num_per_iter)
	    break;
	 if (msgtag == NO_MORE_COLS && sol_id[0] == p->cur_sol.xlevel &&
	     sol_id[1] == p->dcmp_data.iter_num)
	    break;
      }

      if (num_cols >0)
	 add_dcmp_cols(p->dcmp_data.lp_data, &cols,
		       p->par.decomp_col_block_size,
		       p->par.decomp_mat_block_size);
      
      free_dcmp_col_set(&cols);

      return(num_cols);
   }

   /*------------------------------------------------------------------------*
    * If we reach this part of the code, then "wait_for_cols" is not set.
    * However, if block == 1, then this indicates that we should wait for
    * at least one col to come back before exiting. This way we wait after
    * the initial LP solution is submitted before determining that no cols
    * have been generated.
    *------------------------------------------------------------------------*/

   while (TRUE){
      if (block){
	 do{
	    PVM_FUNC(r_bufid, pvm_trecv(ANYONE, ANYTHING, &tout));
	    if (! r_bufid){
	       if (pvm_pstat(p->tree_manager) != PvmOk){
		  printf("TM has died -- decomp exiting\n\n");
		  exit(-502);
	       }
	    }
	 }while (! r_bufid);
      }else{
	 if ((r_bufid = pvm_nrecv(ANYONE, ANYTHING)) < 0) PVM_ERROR(r_bufid);
      }
      if (!r_bufid)
	 break;
      
      pvm_bufinfo(r_bufid, &bytes, &msgtag, &sender);
      num_cols += dcmp_process_message(p, sender, msgtag, &cols, sol_id);
      pvm_freebuf(r_bufid);
      
      if (msgtag == NO_MORE_COLS && sol_id[0] == p->cur_sol.xlevel &&
	  sol_id[1] == p->dcmp_data.iter_num)
	 break;
      
      if (p->par.decomp_max_col_num_per_iter &&
	  num_cols >= p->par.decomp_max_col_num_per_iter)
	 break;
      
      if (num_cols){
	 /* If we received any cols
	    then set block to be false, thus we exit as soon as we have
	    process the rest of the messages in the queue. */
	 block = FALSE;
      }
   }

   if (num_cols >0)
      add_dcmp_cols(p->dcmp_data.lp_data, &cols,
		    p->par.decomp_col_block_size,p->par.decomp_mat_block_size);
   
   free_dcmp_col_set(&cols);
   
   return(num_cols);
}

/*===========================================================================*
 * This function processes one message that arrived during receive_cols.
 *===========================================================================*/
int dcmp_process_message(cg_prob *p, int sender, int msgtag,
		    dcmp_col_set *cols, int *sol_id)
{
   int num_cols = 0, sol_pool_cols;
   double find_cols_time;
   col_data *col;
   LPdata *lp_data = p->dcmp_data.lp_data;
   int info, varnum = lp_data->m;
   int colnum = cols->num_cols, nzcnt, i, is_new_col = FALSE;
   double pivot_el, *unbdd_row = p->dcmp_data.unbdd_row;
   
   switch (msgtag){
    case PACKED_COL:
      /* receive a packed col and add it to the current LP */
      /* check to be sure there is enough room in the col set data structure
	 for another col -- otherwise reallocate memory */
      if (cols->num_cols == cols->max_cols){
	 cols->max_cols += COL_BLOCK_SIZE;
	 cols->lb = (double *) realloc ((char *)cols->lb,
					 (cols->max_cols)*sizeof(double));
	 cols->ub = (double *) realloc ((char *)cols->ub,
					 (cols->max_cols)*sizeof(double));
	 cols->matbeg = (int *) realloc ((char *)cols->matbeg,
					 (cols->max_cols+1)*sizeof(int));
	 cols->obj = (double *) realloc ((char *)cols->obj,
					 (cols->max_cols+1)*sizeof(double));
      }
      if (cols->nzcnt + varnum > cols->max_nzcnt){
	 cols->max_nzcnt += varnum*COL_BLOCK_SIZE;
	 cols->matind = (int *) realloc ((char *)cols->matind,
					 cols->max_nzcnt*sizeof(int));
	 cols->matval = (double *) realloc ((char *)cols->matval,
					    cols->max_nzcnt*sizeof(double));
      }
      
      col = (col_data *) calloc (1, sizeof(col_data));
      if ((info = pvm_upkint(&col->size, 1, 1)) < 0) PVM_ERROR(info);
      col->coef = (char *) calloc (col->size, sizeof(char));
      if ((info = pvm_upkbyte((col->coef), col->size, 1)) < 0) PVM_ERROR(info);
      user_unpack_col(p, col, &nzcnt, cols->matind+cols->matbeg[colnum]);

      /* check to see if the col has a pivot element < 0 in the
       * current solution -- otherwise don't add it --
       * also check to see if its a duplicate */
      
      if (p->dcmp_data.dunbr){
	 for (i = cols->matbeg[colnum], pivot_el = 0; i < nzcnt; i++)
	    pivot_el += unbdd_row[cols->matind[i]];
      }else{
	 pivot_el = -1;
      }
      
      if (pivot_el < - lp_data->lpetol){
	 is_new_col = TRUE;
	 for (i = 0; i < cols->num_cols; i++){
	    /* compare the new col with each of the existing cols */
	    if (cols->matbeg[i+1]-cols->matbeg[i] == nzcnt){
	       if (memcmp((char *)(cols->matind + cols->matbeg[i]),
			  (char *)(cols->matind + cols->matbeg[colnum]),
			  nzcnt*sizeof(int)) == 0){
		  is_new_col = FALSE;
		  break;
	       }
	    }
	 }
      }
      if (is_new_col){
	 if (p->par.verbosity > 4) user_display_col(p, col);
	 /* if we truly have a new constraint here then add it to the col set*/
	 for (i = cols->nzcnt; i < cols->nzcnt+nzcnt; i++){
	    if (lp_data->rhs[cols->matind[i]] != 0){
	       cols->matval[i] = 1;
	    }else{
	       break;
	    }
	 }
	 if (i < cols->nzcnt+nzcnt)
	    break;
	 cols->matind[cols->matbeg[colnum]+nzcnt] = varnum;
	 cols->matval[cols->matbeg[colnum]+nzcnt] = 1;
	 nzcnt++;
	 cols->lb[colnum] = 0;
	 cols->ub[colnum] = 1;
	 cols->matbeg[++cols->num_cols] = cols->matbeg[colnum]+nzcnt;
	 cols->nzcnt += nzcnt;
      }
      FREE(col->coef);
      FREE(col);
      num_cols = 1;
      break;
      
    case NO_MORE_COLS:
      /* this message type says that all cols generated by the current
	 LP solution have been received and hence calculation can
	 resume */
      if ((info = pvm_upkint(&sol_pool_cols, 1, 1)) < 0) PVM_ERROR(info);
      if ((info = pvm_upkdouble(&find_cols_time, 1, 1)) < 0) PVM_ERROR(info);
      if ((info = pvm_upkint(sol_id, 2, 1)) < 0) PVM_ERROR(info);
      if (p->par.verbosity > 3)
	 printf("%i cols added from the solution pool\n", sol_pool_cols);
      break;
      
    default:
      printf("Unknown message type!!\n (%i)", msgtag);
      break;
   }

   return(num_cols);
}  

/*****************************************************************************/
/*****************************************************************************/

void open_decomp_lp(cg_prob *p, int varnum)
{
   LPdata *lp_data;
   int maxn, maxm, maxnz, i;
   
   lp_data = p->dcmp_data.lp_data
           = (LPdata *) calloc (1, sizeof(LPdata));

   open_lp_solver(lp_data);

   lp_data->m = varnum+1;
   lp_data->n = 0;
   maxm = lp_data->maxm = varnum+1;

   /* Should look at whether these sizes should be set more intelligently*/
   maxn = lp_data->maxn = p->par.decomp_max_col_num_per_iter;
   maxnz = lp_data->maxnz = lp_data->maxn*lp_data->maxm;

   lp_data->rhs    = (double *) calloc(maxm, sizeof(double));
   lp_data->sense  = (char *)   calloc(maxm, sizeof(char));
   lp_data->lb     = (double *) calloc(maxn+maxm, sizeof(double));
   lp_data->ub     = (double *) calloc(maxn+maxm, sizeof(double));
   lp_data->obj    = (double *) calloc(maxn+maxm, sizeof(double));
   lp_data->x      = (double *) calloc(maxn, sizeof(double));
   lp_data->matbeg = (int *)    calloc(maxn+maxm+1, sizeof(int));
   lp_data->matval = (double *) calloc(maxnz+maxm, sizeof(double));
   lp_data->matind = (int *)    calloc(maxnz+maxm, sizeof(int));
   lp_data->dj     = (double *) calloc(maxn, sizeof(int));

   p->dcmp_data.unbdd_row = (double *) calloc (maxm, sizeof(double));

   for (i=0; i<maxm; i++)
      lp_data->sense[i] = 'E';

   lp_data->lp_is_modified = LP_HAS_NOT_BEEN_MODIFIED;
   
}   

/*****************************************************************************/
/*****************************************************************************/

void close_decomp_lp(cg_prob *p)
{
   LPdata *lp_data = p->dcmp_data.lp_data;

   FREE(lp_data->x);
   FREE(lp_data->dj);

   free_lp_solver_data(lp_data, TRUE);

   /*close_lp_solver(lp_data);*/

   FREE(p->dcmp_data.lp_data);
   FREE(p->dcmp_data.unbdd_row);
}

/*****************************************************************************/
/*****************************************************************************/

int generate_cuts(cg_prob *p)

{
   LPdata *lp_data = p->dcmp_data.lp_data;
   double *x = lp_data->x;
   int i, num_cols = 0, pos_cols = 0;

   get_x(lp_data);
   
   for (i = 0; i < lp_data->n; i++){
      if (x[i] > 0){
	 pos_cols++;
	 num_cols += user_check_col(p, lp_data->matind+lp_data->matbeg[i],
				     lp_data->matval+lp_data->matbeg[i],
				     lp_data->matbeg[i+1]-lp_data->matbeg[i]);
      }
   }
   printf("There are %i columns at nonzero level\n", pos_cols);
   return(num_cols);
}

/*****************************************************************************/
/*****************************************************************************/

int generate_new_cols(cg_prob *p)
{
   dcmp_col_set *cols, cols_to_add;
   col_data *packed_col = (col_data *) calloc (1, sizeof(col_data));
   LPdata *lp_data = p->dcmp_data.lp_data;
   int i, j, k, info, nzcnt, col_count, s_bufid;
   double etol = lp_data->lpetol;

   cols = user_generate_new_cols(p);

   if (cols->num_cols <= 0){
      free_dcmp_col_set(cols);
      FREE(cols);
      FREE(packed_col)
      return(0);
   }
   
   cols_to_add.lb = (double *) calloc (cols->num_cols, sizeof(double));
   cols_to_add.ub = (double *) calloc (cols->num_cols, sizeof(double));
   cols_to_add.matbeg = (int *) calloc (cols->num_cols+1, sizeof(int));
   cols_to_add.matind = (int *) calloc (cols->nzcnt, sizeof(int));
   cols_to_add.matval = (double *) calloc (cols->nzcnt, sizeof(double));
   cols_to_add.obj = (double *) calloc (cols->num_cols, sizeof(double));
   cols_to_add.num_cols = 0;
   cols_to_add.max_cols = cols->num_cols;
   cols_to_add.nzcnt = 0;
   cols_to_add.max_nzcnt = cols->nzcnt;
   cols_to_add.bd_type = 4;

   for (i = 0, nzcnt = 0, col_count = 0; i < cols->num_cols; i++){
      for (j = cols->matbeg[i], k = 0; j<cols->matbeg[i+1] && k < lp_data->m;
	   k++){
	 if (lp_data->rhs[k] < etol){
	    if (cols->matind[j] == k)
	       break;
	    else
	       continue;
	 }
	 if (lp_data->rhs[k] > 1-etol && cols->matind[j] != k)
	    break;
	 if (cols->matind[j] == k){
	    cols_to_add.matval[nzcnt] = 1;
	    cols_to_add.matind[nzcnt++] = cols->matind[j++];
	 }
      }
      if (j < cols->matbeg[i+1])
	 continue;

      cols_to_add.matind[nzcnt] = lp_data->m-1;
      cols_to_add.matval[nzcnt++] = 1;
      cols_to_add.lb[col_count] = 0;
      cols_to_add.ub[col_count++] = 1;
      cols_to_add.matbeg[col_count] = nzcnt;

      if (p->sol_pool){
	 user_pack_col(cols->matind+cols->matbeg[i],
		       cols->matbeg[i+1]-cols->matbeg[i], packed_col);
	 
	 if ((s_bufid = pvm_initsend(PvmDataRaw)) < 0) PVM_ERROR(s_bufid);
	 if ((info = pvm_pkint(&packed_col->size, 1, 1)) < 0) PVM_ERROR(info);
	 if ((info = pvm_pkint(&p->cur_sol.xlevel, 1, 1)) < 0) PVM_ERROR(info);
	 if ((info = pvm_pkbyte(packed_col->coef, packed_col->size, 1)) < 0)
	    PVM_ERROR(info);
	 if ((info = pvm_send(p->sol_pool, PACKED_COL)) < 0) PVM_ERROR(info);
	 if ((info = pvm_freebuf(s_bufid)) < 0) PVM_ERROR(info);
      }
      
      FREE(packed_col->coef);
   }
   cols_to_add.num_cols = col_count;
   cols_to_add.nzcnt = nzcnt;

   add_dcmp_cols(lp_data, &cols_to_add, p->par.decomp_col_block_size,
		 p->par.decomp_mat_block_size);

   free_dcmp_col_set(&cols_to_add);
   free_dcmp_col_set(cols);
   FREE(cols);
   FREE(packed_col);

   return(col_count);
}

void get_cols_from_pool(cg_prob *p, int tid)
{
   LPdata *lp_data = p->dcmp_data.lp_data;
   double etol = lp_data->lpetol;
   int varnum = lp_data->m-1;
   int *ind = NULL, *rhs_ind;
   double *val = NULL, *unbdd_row = p->dcmp_data.unbdd_row, *rhs_val;
   int nzcnt = 0, rhs_nzcnt, i, s_bufid, info;
   double *rhs = lp_data->rhs;
   int dunbr = p->dcmp_data.dunbr;

   if (dunbr){
      memset((char *)unbdd_row, 0, (varnum+1)*sizeof(double));
      unbdd_row[dunbr-1] = -1;
      btran(lp_data, unbdd_row);
   }

   if (!(p->dcmp_data.iter_num%p->par.decomp_sol_pool_check_freq == 0)
       || tid == 0)
      return;

   if (dunbr){
      ind = (int *) calloc (varnum, sizeof(int));
      val = (double *) calloc (varnum, sizeof(double));
   }
   
   rhs_ind = (int *) calloc (varnum, sizeof(int));
   rhs_val = (double *) calloc (varnum, sizeof(double));

   /* xind is a list of the indices correspondoing to the nonzeros variables
      in the current lp solution. xval contains the actual values of these
      variables */
   if (dunbr){
      for (nzcnt = i = 0; i < varnum; i++){
	 if (unbdd_row[i] > etol || unbdd_row[i] < -etol){
	    ind[nzcnt] = i;
	    val[nzcnt++] = unbdd_row[i];
	 }
      }
   }
   for (rhs_nzcnt = i = 0; i < varnum; i++){
      if (rhs[i] > etol){
	 rhs_ind[rhs_nzcnt] = i;
	 rhs_val[rhs_nzcnt++] = rhs[i];
      }
   }
   if (dunbr && (ind[nzcnt-1] != lp_data->m-1)){
      ind[nzcnt] = lp_data->m-1;
      val[nzcnt++] = 0;
   }
   
   /* send the data */
   if ((s_bufid = pvm_initsend(PvmDataRaw)) < 0) PVM_ERROR(s_bufid);
   if ((info = pvm_pkint(&nzcnt, 1, 1)) < 0) PVM_ERROR(info);
   if (nzcnt){
      if ((info = pvm_pkint(ind, nzcnt, 1)) < 0) PVM_ERROR(info);
      if ((info = pvm_pkdouble(val, nzcnt, 1)) < 0) PVM_ERROR(info);
   }
   if ((info = pvm_pkint(&rhs_nzcnt, 1, 1)) < 0) PVM_ERROR(info);
   if ((info = pvm_pkint(rhs_ind, rhs_nzcnt, 1)) < 0) PVM_ERROR(info);
   if ((info = pvm_pkdouble(rhs_val, rhs_nzcnt, 1)) < 0) PVM_ERROR(info);
   if ((pvm_pkint(&p->cur_sol.xlevel, 1, 1)) < 0) PVM_ERROR(info);
   if ((info = pvm_pkint(&p->dcmp_data.iter_num, 1, 1)) < 0) PVM_ERROR(info);
   if ((info = pvm_send(tid, CG_LP_SOLUTION)) < 0) PVM_ERROR(info);
   
   FREE(ind);
   FREE(val);
   FREE(rhs_ind);
   FREE(rhs_val);
}

void add_dcmp_cols(LPdata *lp_data, dcmp_col_set *cols, int col_block_size,
		  int mat_block_size)
{
   char *where_to_move = (char *) calloc(cols->num_cols, sizeof(char));

   if (lp_data->n + cols->num_cols > lp_data->maxn ||
       lp_data->nz + cols->nzcnt > lp_data->maxnz){
      /*Currently, this should never happen since we allocate enough space up
	front. However, should think about changing this */
      printf("Error: Resizing LP in decomp. Aborting...\n\n");
      exit(1);
#if 0
      resize_lp(lp_data, 0, col_block_size, mat_block_size, 0, cols->num_cols,
		cols->nzcnt, &maxm, &maxn, &maxnz);
      if (maxn > lp_data->maxn){
	 lp_data->maxn = maxn;
	 lp_data->x = (double *) realloc(lp_data->x, maxn * DSIZE);
	 lp_data->dj = (double *) realloc(lp_data->dj, maxn * DSIZE);
      }
#endif
   }
   
   add_cols(lp_data, cols->num_cols, cols->nzcnt, cols->obj, cols->matbeg,
	    cols->matind, cols->matval, cols->lb, cols->ub, where_to_move);
}

void free_dcmp_col_set(dcmp_col_set *cols)
{
   FREE(cols->obj);
   FREE(cols->lb);
   FREE(cols->ub);
   FREE(cols->matbeg);
   FREE(cols->matind);
   FREE(cols->matval);
}
