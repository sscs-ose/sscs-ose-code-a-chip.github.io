#ifndef _DECOMP_H
#define _DECOMP_H

#include "sym_proto.h"
#include "sym_cg.h"
#include "decomp_types.h"

int create_initial_lp PROTO((cg_prob *p));
int decomp PROTO((cg_prob *p));
int receive_cols PROTO((cg_prob *p));
int dcmp_process_message PROTO((cg_prob *p, int sender, int msgtag,
				dcmp_col_set *cols, int *sol_id));
void open_decomp_lp PROTO((cg_prob *p, int varnum));
void close_decomp_lp PROTO((cg_prob *p));
int generate_cuts PROTO((cg_prob *p));
/*int add_cols PROTO((cg_prob *p, col_data **cols, int num_cols));*/
void get_cols_from_pool PROTO((cg_prob *p, int tid));
int generate_new_cols PROTO((cg_prob *p));
void add_dcmp_cols PROTO((LPdata *lp_data, dcmp_col_set *cols,
			 int col_block_size, int mat_block_size));
void free_dcmp_col_set PROTO((dcmp_col_set *cols));

/*===== User supplied routines ======================================*/

dcmp_col_set *user_generate_new_cols PROTO((cg_prob *p));
void user_unpack_col PROTO((cg_prob *p, col_data *col, int *nzcnt,
			    int *matind));
void user_display_col PROTO((cg_prob *p, col_data *col));
int user_check_col PROTO((cg_prob *p, int *colind, double *colval,
			  int collen));
void user_pack_col PROTO((int *colind, int collen, col_data *packed_col));
void user_free_decomp_data_structures PROTO((cg_prob *p, void **user));
char user_set_rhs PROTO((int varnum, double *rhs, int length, int *ind,
			 double *val, void *user));
void user_send_to_sol_pool PROTO((cg_prob *p));

#endif
