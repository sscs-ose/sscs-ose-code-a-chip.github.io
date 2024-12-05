#ifndef _SOL_POOL_PARAMS_H
#define _SOL_POOL_PARAMS_H

typedef struct SOL_POOL_PARAMS{
   int     verbosity;
   double  etol;
   int     block_size;
   int     delete_which;
   int     max_size;
   int     max_number_of_sols;
   int     min_to_delete;
   int     check_which;
   int     touches_until_deletion;
   int     compress_num;
   double  compress_ratio;
}sp_params;

/* parameter values for "check_which_cuts" */
#define CHECK_ALL_COLS              0
#define CHECK_COL_LEVEL             1
#define CHECK_COL_TOUCHES           2
#define CHECK_COL_LEVEL_AND_TOUCHES 3

/* parameter values for "delete_which_cuts" */
#define DELETE_DUPLICATE_COLS                  1
#define DELETE_DUPLICATE_AND_INEFFECTIVE_COLS  2

#endif
