#ifndef _ILP_SOLVER_IF_H_
#define _ILP_SOLVER_IF_H_

enum class SOLVER_ENUM {Cbc, SYMPHONY};

class ILPSolverIf {
  private:
    SOLVER_ENUM _se;
    int _t, _nvar, _nrow;
    void* _solver;
    double *_sol;

  public:
    ILPSolverIf(const SOLVER_ENUM& se = SOLVER_ENUM::Cbc);
    ~ILPSolverIf();
    double getInfinity() const;
    void setTimeLimit(const int t) { _t = t; }

    void loadProblem(const int nvar, const int nrow, const int* start,
        const int* indices, const double* values, const double* varlb, const double* varub,
        const double* obj, const double* rowlb, const double* rowub, const int* intvars = nullptr);
    void loadProblemSym(int nvar, int nrow, int* start,
        int* indices, double* values, double* varlb, double* varub,
        char *intvars, double* obj, char *sens, double *rhs); 

    int solve(const int num_threads = 1);
    double *solution() { return _sol; }
    void writelp(char* filename, char **varnames = nullptr, char **colnames = nullptr);
};
#endif
