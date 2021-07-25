## THIS IS FILE IS FROM https://github.com/turulomio/reusingcode IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT
## DO NOT UPDATE IT IN YOUR CODE IT WILL BE REPLACED USING FUNCTION IN README

from logging import error
from scipy.stats import linregress

class LinealRegression:
    def __init__(self,name_y="Y", name_x="X"):
        self.name_y=name_y
        self.name_x=name_x
        self.X=[]
        self.Y=[]

    def append(self, y, x):
        self.X.append(float(x))
        self.Y.append(float(y))

    def set_lists(self, list_y, list_x):
        if len(list_y)!=len(list_x):
            error("Length of lists is different")
            return
        del self.X
        del self.Y
        self.Y=list_y
        self.X=list_x

    def calculate(self):
        self.slope, self.intercept, self.r_value, self.p_value, self.std_err=linregress(self.X,self.Y)
        self.r_squared=self.r_value**2

    def string(self, with_names=False):
        if with_names is False:
            return f"Y = {self.slope} X + {self.intercept}"
        else:
            return f"'{self.name_y}' = {self.slope} '{self.name_x}' + {self.intercept}"

    def r_squared_string(self):
        return f"R²={self.r_squared}"



if __name__ == "__main__":
    lr=LinealRegression()
    lr.set_lists((4,8,12,),(1,2,3))
    lr.calculate()
    print(lr.string())

    lr=LinealRegression()
    lr.set_lists((7,7,6,4),(5,3,3,1))
    lr.calculate()
    print(lr.string())
