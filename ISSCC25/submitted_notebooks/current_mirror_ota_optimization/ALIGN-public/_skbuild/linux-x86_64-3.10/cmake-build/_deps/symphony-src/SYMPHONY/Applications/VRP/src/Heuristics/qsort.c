/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was modified by Ali Pilatin January, 2005 (alp8@lehigh.edu)     */
/*                                                                           */
/* (c) Copyright 2000-2005 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include "qsort.h"

void exchange(sweep_data *data, int i, int j)
{

  sweep_data temp;

  temp=data[i];
  data[i]=data[j];
  data[j]=temp;
}

/*===========================================================================*/

int partition(sweep_data *data, int len)
{

  int i=0, j, pivot;
  float middle;

  j=len-1;
  /*pivot=random() % len;*/
  pivot=0;
  middle=data[pivot].angle;

  exchange(data, pivot, j);

  while (i<j){
    while ((i<j) && (data[i].angle<=middle))
      i++;
    while ((i<j) && (data[j].angle>=middle))
      j--;
    if (i<j)
      exchange(data, i, j);
  }
  if (i!=len-1)
    exchange(data, i, len-1);

  return(i);
}

/*===========================================================================*/

void quicksort(sweep_data *data, int len)
{

  int pivot;

  pivot=partition(data, len);
    
  if (pivot>=2)
    quicksort(data, pivot);
  if (pivot <= len - 3)
    quicksort(data+pivot+1, len-pivot-1);
}

