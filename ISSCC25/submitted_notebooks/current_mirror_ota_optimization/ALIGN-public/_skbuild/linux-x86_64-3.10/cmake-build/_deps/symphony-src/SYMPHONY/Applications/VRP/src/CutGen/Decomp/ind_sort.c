#include "ind_sort.h"

void exchange(int *ind_list, double *vals, int i, int j)
{
  int temp_int;
  double temp_dbl;

  temp_int = ind_list[i];
  ind_list[i] = ind_list[j];
  ind_list[j] = temp_int;

  temp_dbl = vals[i];
  vals[i] = vals[j];
  vals[j] = temp_dbl;
}

/*===========================================================================*/

int partition(int *ind_list, double *vals, int len)
{

  int i=0, j, pivot;
  double middle;

  j=len-1;
  /*pivot=random() % len;*/
  pivot=0;
  middle = vals[pivot];

  exchange(ind_list, vals, pivot, j);

  while (i<j){
    while ((i<j) && (vals[i] >= middle))
       i++;
    while ((i<j) && (vals[j] <= middle))
       j--;
    if (i<j)
      exchange(ind_list, vals, i, j);
  }
  if (i!=len-1)
    exchange(ind_list, vals, i, len-1);

  return(i);
}

/*===========================================================================*/

void ind_sort(int *ind_list, double *vals, int len)
{

  int pivot;

  pivot=partition(ind_list, vals, len);
    
  if (pivot>=2)
    ind_sort(ind_list, vals, pivot);
  if (pivot <= len - 3)
    ind_sort(ind_list+pivot+1, vals+pivot+1, len-pivot-1);
}

