/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The author of this file is Menal Guzelsoy                                 */
/*                                                                           */
/* (c) Copyright 2006-2019 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

// OsiSymSolverInterfaceTest.cpp adapted from OsiCpxSolverInterfaceTest.cpp

#include "CoinPragma.hpp"
#include "OsiSymSolverInterface.hpp"
#include "OsiCuts.hpp"
#include "OsiRowCut.hpp"
#include "OsiUnitTests.hpp"
#include "CoinPackedMatrix.hpp"

#include "symphony.h"

//--------------------------------------------------------------------------
void OsiSymSolverInterfaceUnitTest( const std::string & mpsDir, const std::string & netlibDir )
{  
  // Test default constructor
  {
    OsiSymSolverInterface m;
    OSIUNITTEST_ASSERT_ERROR(m.getNumCols()         == 0,    {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.obj_                 == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.collower_            == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.colupper_            == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.rowsense_            == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.rhs_                 == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.rowrange_            == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.rowlower_            == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.rowupper_            == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.colsol_              == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.matrixByRow_         == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.matrixByCol_         == NULL, {}, "symphony", "default constructor");
    OSIUNITTEST_ASSERT_ERROR(m.getApplicationData() == NULL, {}, "symphony", "default constructor");
    int i=2346;
    m.setApplicationData(&i);
    OSIUNITTEST_ASSERT_ERROR(*((int *)(m.getApplicationData())) == i, {}, "symphony", "set application data");
  }

  {    
    CoinRelFltEq eq;
    OsiSymSolverInterface m;
    std::string fn = mpsDir+"exmip1.mps";
    m.readMps(const_cast<char *>(fn.c_str()));
    int ad = 13579;
    m.setApplicationData(&ad);

    {
      OSIUNITTEST_ASSERT_ERROR(m.getNumCols() == 8, {}, "symphony", "read exmip1");
      const CoinPackedMatrix * colCopy = m.getMatrixByCol();
      OSIUNITTEST_ASSERT_ERROR(colCopy->getNumCols()  == 8, {}, "symphony", "exmip1 matrix");
      OSIUNITTEST_ASSERT_ERROR(colCopy->getMajorDim() == 8, {}, "symphony", "exmip1 matrix");
      OSIUNITTEST_ASSERT_ERROR(colCopy->getNumRows()  == 5, {}, "symphony", "exmip1 matrix");
      OSIUNITTEST_ASSERT_ERROR(colCopy->getMinorDim() == 5, {}, "symphony", "exmip1 matrix");
      OSIUNITTEST_ASSERT_ERROR(colCopy->getVectorLengths()[7] == 2, {}, "symphony", "exmip1 matrix");
      CoinPackedMatrix revColCopy;
      revColCopy.reverseOrderedCopyOf(*colCopy);
      CoinPackedMatrix rev2ColCopy;      
      rev2ColCopy.reverseOrderedCopyOf(revColCopy);
      OSIUNITTEST_ASSERT_ERROR(rev2ColCopy.getNumCols()  == 8, {}, "symphony", "twice reverse matrix copy");
      OSIUNITTEST_ASSERT_ERROR(rev2ColCopy.getMajorDim() == 8, {}, "symphony", "twice reverse matrix copy");
      OSIUNITTEST_ASSERT_ERROR(rev2ColCopy.getNumRows()  == 5, {}, "symphony", "twice reverse matrix copy");
      OSIUNITTEST_ASSERT_ERROR(rev2ColCopy.getMinorDim() == 5, {}, "symphony", "twice reverse matrix copy");
      OSIUNITTEST_ASSERT_ERROR(rev2ColCopy.getVectorLengths()[7] == 2, {}, "symphony", "twice reverse matrix copy");
    }
    
    // Test copy constructor and assignment operator
    {
      OsiSymSolverInterface lhs;
      {      
        OSIUNITTEST_ASSERT_ERROR(*((int *)( m.getApplicationData())) == ad, {}, "symphony", "set application data");
        OsiSymSolverInterface im(m);   
        OSIUNITTEST_ASSERT_ERROR(*((int *)(im.getApplicationData())) == ad, {}, "symphony", "application data is copied");

        OsiSymSolverInterface imC1(im);
        OSIUNITTEST_ASSERT_ERROR(imC1.getSymphonyEnvironment() != im.getSymphonyEnvironment(), {}, "symphony", "copy constructor");
        OSIUNITTEST_ASSERT_ERROR(imC1.getNumCols()  == im.getNumCols(), {}, "symphony", "copy constructor");
        OSIUNITTEST_ASSERT_ERROR(imC1.getNumRows()  == im.getNumRows(), {}, "symphony", "copy constructor");
        
        OsiSymSolverInterface imC2(im);
        OSIUNITTEST_ASSERT_ERROR(imC1.getSymphonyEnvironment() != im.getSymphonyEnvironment(), {}, "symphony", "copy constructor");
        OSIUNITTEST_ASSERT_ERROR(imC1.getSymphonyEnvironment() != imC2.getSymphonyEnvironment(), {}, "symphony", "copy constructor");
        OSIUNITTEST_ASSERT_ERROR(imC2.getNumCols()  == im.getNumCols(), {}, "symphony", "copy constructor");
        OSIUNITTEST_ASSERT_ERROR(imC2.getNumRows()  == im.getNumRows(), {}, "symphony", "copy constructor");

        lhs = imC2;
      }

      // Test that lhs has correct values even though rhs has gone out of scope
      OSIUNITTEST_ASSERT_ERROR(lhs.getSymphonyEnvironment() != m.getSymphonyEnvironment(), {}, "symphony", "copy constructor");
      OSIUNITTEST_ASSERT_ERROR(lhs.getNumCols() == m.getNumCols(), {}, "symphony", "copy constructor");
      OSIUNITTEST_ASSERT_ERROR(lhs.getNumRows() == m.getNumRows(), {}, "symphony", "copy constructor");
      OSIUNITTEST_ASSERT_ERROR(*((int *)(lhs.getApplicationData())) == ad, {}, "symphony", "copy constructor");
    }
    
    // Test clone
    {
      OsiSymSolverInterface symSi(m);
      OsiSolverInterface * siPtr = &symSi;
      OsiSolverInterface * siClone = siPtr->clone();
      OsiSymSolverInterface * symClone = dynamic_cast<OsiSymSolverInterface*>(siClone);
      OSIUNITTEST_ASSERT_ERROR(symClone != NULL, {}, "symphony", "clone");
      OSIUNITTEST_ASSERT_ERROR(symClone->getSymphonyEnvironment() != symSi.getSymphonyEnvironment(), {}, "symphony", "clone");
      OSIUNITTEST_ASSERT_ERROR(symClone->getNumRows() == symSi.getNumRows(), {}, "symphony", "clone");
      OSIUNITTEST_ASSERT_ERROR(symClone->getNumCols() == m.getNumCols(), {}, "symphony", "clone");
      OSIUNITTEST_ASSERT_ERROR(*((int *)(symClone->getApplicationData())) == ad, {}, "symphony", "clone");
      
      delete siClone;
    }

    // test infinity
    {
      OsiSymSolverInterface si;
      OSIUNITTEST_ASSERT_ERROR(si.getInfinity() == SYM_INFINITY, {}, "symphony", "infinity");
    }     

    {
      OsiSymSolverInterface symSi(m);
      int nc = symSi.getNumCols();
      int nr = symSi.getNumRows();
      const double * cl = symSi.getColLower();
      const double * cu = symSi.getColUpper();
      const double * rl = symSi.getRowLower();
      const double * ru = symSi.getRowUpper();

      OSIUNITTEST_ASSERT_ERROR(nc == 8, return, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(nr == 5, return, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(cl[0],2.5), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(cl[1],0.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(cu[1],4.1), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(cu[2],1.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(rl[0],2.5), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(rl[4],3.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(ru[1],2.1), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(ru[4],15.), {}, "symphony", "read and copy exmip1");

      symSi.branchAndBound();
      const double * cs = symSi.getColSolution();
      OSIUNITTEST_ASSERT_ERROR(eq(cs[0],2.5), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(cs[6],0.0), {}, "symphony", "read and copy exmip1");

      OSIUNITTEST_ASSERT_ERROR(!eq(cl[3],1.2345), {}, "symphony", "set col lower");
      symSi.setColLower( 3, 1.2345 );
      OSIUNITTEST_ASSERT_ERROR( eq(symSi.getColLower()[3],1.2345), {}, "symphony", "set col lower");

      OSIUNITTEST_ASSERT_ERROR(!eq(symSi.getColUpper()[4],10.2345), {}, "symphony", "set col upper");
      symSi.setColUpper( 4, 10.2345 );
      OSIUNITTEST_ASSERT_ERROR( eq(symSi.getColUpper()[4],10.2345), {}, "symphony", "set col upper");

#if 0
      /* FIXME: SYMPHONY will throw an error because of the infeasiblity of the solution! */
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjValue(),3.5), {}, "symphony", "getObjValue() before solve");
#endif

      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[0], 1.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[1], 0.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[2], 0.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[3], 0.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[4], 2.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[5], 0.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[6], 0.0), {}, "symphony", "read and copy exmip1");
      OSIUNITTEST_ASSERT_ERROR(eq(symSi.getObjCoefficients()[7],-1.0), {}, "symphony", "read and copy exmip1");
    }
    
    // Test getMatrixByRow method
    { 
      const OsiSymSolverInterface si(m);
      const CoinPackedMatrix * smP = si.getMatrixByRow();
      
      OSIUNITTEST_ASSERT_ERROR(smP->getMajorDim()    ==  5, return, "symphony", "getMatrixByRow: major dim");
      OSIUNITTEST_ASSERT_ERROR(smP->getNumElements() == 14, return, "symphony", "getMatrixByRow: num elements");

      CoinRelFltEq eq;
      const double * ev = smP->getElements();
      OSIUNITTEST_ASSERT_ERROR(eq(ev[0],   3.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[1],   1.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[2],  -2.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[3],  -1.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[4],  -1.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[5],   2.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[6],   1.1), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[7],   1.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[8],   1.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[9],   2.8), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[10], -1.2), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[11],  5.6), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[12],  1.0), {}, "symphony", "getMatrixByRow: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[13],  1.9), {}, "symphony", "getMatrixByRow: elements");
      
      const int * mi = smP->getVectorStarts();
      OSIUNITTEST_ASSERT_ERROR(mi[0] ==  0, {}, "symphony", "getMatrixByRow: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[1] ==  5, {}, "symphony", "getMatrixByRow: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[2] ==  7, {}, "symphony", "getMatrixByRow: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[3] ==  9, {}, "symphony", "getMatrixByRow: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[4] == 11, {}, "symphony", "getMatrixByRow: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[5] == 14, {}, "symphony", "getMatrixByRow: vector starts");
      
      const int * ei = smP->getIndices();
      OSIUNITTEST_ASSERT_ERROR(ei[ 0] == 0, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 1] == 1, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 2] == 3, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 3] == 4, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 4] == 7, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 5] == 1, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 6] == 2, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 7] == 2, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 8] == 5, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 9] == 3, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[10] == 6, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[11] == 0, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[12] == 4, {}, "symphony", "getMatrixByRow: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[13] == 7, {}, "symphony", "getMatrixByRow: indices");
    }

    //--------------
    // Test rowsense, rhs, rowrange, getMatrixByRow
    {
      OsiSymSolverInterface lhs;
      {     
        OsiSymSolverInterface siC1(m);

        const char   * siC1rs  = siC1.getRowSense();
        OSIUNITTEST_ASSERT_ERROR(siC1rs[0] == 'G', {}, "symphony", "row sense");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[1] == 'L', {}, "symphony", "row sense");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[2] == 'E', {}, "symphony", "row sense");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[3] == 'R', {}, "symphony", "row sense");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[4] == 'R', {}, "symphony", "row sense");
        
        const double * siC1rhs = siC1.getRightHandSide();
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[0],2.5), {}, "symphony", "right hand side");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[1],2.1), {}, "symphony", "right hand side");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[2],4.0), {}, "symphony", "right hand side");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[3],5.0), {}, "symphony", "right hand side");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[4],15.), {}, "symphony", "right hand side");
        
        const double * siC1rr  = siC1.getRowRange();
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[0],0.0), {}, "symphony", "row range");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[1],0.0), {}, "symphony", "row range");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[2],0.0), {}, "symphony", "row range");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[3],5.0-1.8), {}, "symphony", "row range");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[4],15.0-3.0), {}, "symphony", "row range");
        
        const CoinPackedMatrix * siC1mbr = siC1.getMatrixByRow();
        OSIUNITTEST_ASSERT_ERROR(siC1mbr != NULL, {}, "symphony", "matrix by row");
        OSIUNITTEST_ASSERT_ERROR(siC1mbr->getMajorDim()    ==  5, return, "symphony", "matrix by row: major dim");
        OSIUNITTEST_ASSERT_ERROR(siC1mbr->getNumElements() == 14, return, "symphony", "matrix by row: num elements");
        
        const double * ev = siC1mbr->getElements();
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 0], 3.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 1], 1.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 2],-2.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 3],-1.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 4],-1.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 5], 2.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 6], 1.1), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 7], 1.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 8], 1.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[ 9], 2.8), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[10],-1.2), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[11], 5.6), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[12], 1.0), {}, "symphony", "matrix by row: elements");
        OSIUNITTEST_ASSERT_ERROR(eq(ev[13], 1.9), {}, "symphony", "matrix by row: elements");

        const CoinBigIndex * mi = siC1mbr->getVectorStarts();
        OSIUNITTEST_ASSERT_ERROR(mi[0] ==  0, {}, "symphony", "matrix by row: vector starts");
        OSIUNITTEST_ASSERT_ERROR(mi[1] ==  5, {}, "symphony", "matrix by row: vector starts");
        OSIUNITTEST_ASSERT_ERROR(mi[2] ==  7, {}, "symphony", "matrix by row: vector starts");
        OSIUNITTEST_ASSERT_ERROR(mi[3] ==  9, {}, "symphony", "matrix by row: vector starts");
        OSIUNITTEST_ASSERT_ERROR(mi[4] == 11, {}, "symphony", "matrix by row: vector starts");
        OSIUNITTEST_ASSERT_ERROR(mi[5] == 14, {}, "symphony", "matrix by row: vector starts");
        
        const int * ei = siC1mbr->getIndices();
        OSIUNITTEST_ASSERT_ERROR(ei[ 0] == 0, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 1] == 1, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 2] == 3, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 3] == 4, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 4] == 7, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 5] == 1, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 6] == 2, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 7] == 2, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 8] == 5, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[ 9] == 3, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[10] == 6, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[11] == 0, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[12] == 4, {}, "symphony", "matrix by row: indices");
        OSIUNITTEST_ASSERT_ERROR(ei[13] == 7, {}, "symphony", "matrix by row: indices");

        /* SYMPHONY will return another pointer! */
        OSIUNITTEST_ASSERT_WARNING(siC1rs  == siC1.getRowSense(), {}, "symphony", "row sense");
        OSIUNITTEST_ASSERT_WARNING(siC1rhs == siC1.getRightHandSide(), {}, "symphony", "right hand side");
        OSIUNITTEST_ASSERT_WARNING(siC1rr  == siC1.getRowRange(), {}, "symphony", "row range");

        // Change SYM Model by adding free row
        OsiRowCut rc;
        rc.setLb(-COIN_DBL_MAX);
        rc.setUb( COIN_DBL_MAX);
        OsiCuts cuts;
        cuts.insert(rc);
        siC1.applyCuts(cuts);

        siC1rs  = siC1.getRowSense();
        OSIUNITTEST_ASSERT_ERROR(siC1rs[0] == 'G', {}, "symphony", "row sense after adding row");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[1] == 'L', {}, "symphony", "row sense after adding row");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[2] == 'E', {}, "symphony", "row sense after adding row");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[3] == 'R', {}, "symphony", "row sense after adding row");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[4] == 'R', {}, "symphony", "row sense after adding row");
        OSIUNITTEST_ASSERT_ERROR(siC1rs[5] == 'N', {}, "symphony", "row sense after adding row");

        siC1rhs = siC1.getRightHandSide();
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[0],2.5), {}, "symphony", "right hand side after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[1],2.1), {}, "symphony", "right hand side after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[2],4.0), {}, "symphony", "right hand side after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[3],5.0), {}, "symphony", "right hand side after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[4],15.), {}, "symphony", "right hand side after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rhs[5],0.0), {}, "symphony", "right hand side after adding row");

        siC1rr  = siC1.getRowRange();
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[0],0.0), {}, "symphony", "row range after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[1],0.0), {}, "symphony", "row range after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[2],0.0), {}, "symphony", "row range after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[3],5.0-1.8), {}, "symphony", "row range after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[4],15.0-3.0), {}, "symphony", "row range after adding row");
        OSIUNITTEST_ASSERT_ERROR(eq(siC1rr[5],0.0), {}, "symphony", "row range after adding row");
    
        lhs = siC1;
      }
      // Test that lhs has correct values even though siC1 has gone out of scope
      const char * lhsrs  = lhs.getRowSense();
      OSIUNITTEST_ASSERT_ERROR(lhsrs[0] == 'G', {}, "symphony", "row sense after assignment");
      OSIUNITTEST_ASSERT_ERROR(lhsrs[1] == 'L', {}, "symphony", "row sense after assignment");
      OSIUNITTEST_ASSERT_ERROR(lhsrs[2] == 'E', {}, "symphony", "row sense after assignment");
      OSIUNITTEST_ASSERT_ERROR(lhsrs[3] == 'R', {}, "symphony", "row sense after assignment");
      OSIUNITTEST_ASSERT_ERROR(lhsrs[4] == 'R', {}, "symphony", "row sense after assignment");
      OSIUNITTEST_ASSERT_ERROR(lhsrs[5] == 'N', {}, "symphony", "row sense after assignment");
      
      const double * lhsrhs = lhs.getRightHandSide();
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrhs[0],2.5), {}, "symphony", "right hand side after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrhs[1],2.1), {}, "symphony", "right hand side after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrhs[2],4.0), {}, "symphony", "right hand side after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrhs[3],5.0), {}, "symphony", "right hand side after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrhs[4],15.), {}, "symphony", "right hand side after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrhs[5],0.0), {}, "symphony", "right hand side after assignment");
      
      const double *lhsrr = lhs.getRowRange();
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrr[0],0.0), {}, "symphony", "row range after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrr[1],0.0), {}, "symphony", "row range after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrr[2],0.0), {}, "symphony", "row range after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrr[3],5.0-1.8), {}, "symphony", "row range after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrr[4],15.0-3.0), {}, "symphony", "row range after assignment");
      OSIUNITTEST_ASSERT_ERROR(eq(lhsrr[5],0.0), {}, "symphony", "row range after assignment");
      
      const CoinPackedMatrix * lhsmbr = lhs.getMatrixByRow();
      OSIUNITTEST_ASSERT_ERROR(lhsmbr != NULL, {}, "symphony", "matrix by row after assignment");
      OSIUNITTEST_ASSERT_ERROR(lhsmbr->getMajorDim()    ==  6, return, "symphony", "matrix by row after assignment: major dim");
      OSIUNITTEST_ASSERT_ERROR(lhsmbr->getNumElements() == 14, return, "symphony", "matrix by row after assignment: num elements");

      const double * ev = lhsmbr->getElements();
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 0], 3.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 1], 1.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 2],-2.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 3],-1.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 4],-1.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 5], 2.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 6], 1.1), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 7], 1.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 8], 1.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[ 9], 2.8), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[10],-1.2), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[11], 5.6), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[12], 1.0), {}, "symphony", "matrix by row after assignment: elements");
      OSIUNITTEST_ASSERT_ERROR(eq(ev[13], 1.9), {}, "symphony", "matrix by row after assignment: elements");
      
      const CoinBigIndex * mi = lhsmbr->getVectorStarts();
      OSIUNITTEST_ASSERT_ERROR(mi[0] ==  0, {}, "symphony", "matrix by row after assignment: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[1] ==  5, {}, "symphony", "matrix by row after assignment: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[2] ==  7, {}, "symphony", "matrix by row after assignment: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[3] ==  9, {}, "symphony", "matrix by row after assignment: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[4] == 11, {}, "symphony", "matrix by row after assignment: vector starts");
      OSIUNITTEST_ASSERT_ERROR(mi[5] == 14, {}, "symphony", "matrix by row after assignment: vector starts");
      
      const int * ei = lhsmbr->getIndices();
      OSIUNITTEST_ASSERT_ERROR(ei[ 0] == 0, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 1] == 1, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 2] == 3, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 3] == 4, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 4] == 7, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 5] == 1, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 6] == 2, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 7] == 2, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 8] == 5, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[ 9] == 3, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[10] == 6, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[11] == 0, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[12] == 4, {}, "symphony", "matrix by row after assignment: indices");
      OSIUNITTEST_ASSERT_ERROR(ei[13] == 7, {}, "symphony", "matrix by row after assignment: indices");
    }
  }
    
  // Do common solverInterface testing by calling the base class testing method.
#if 0
  {
     OsiSymSolverInterface m;
     OsiSolverInterfaceCommonUnitTest(&m, mpsDir,netlibDir);
  }
#endif
}
