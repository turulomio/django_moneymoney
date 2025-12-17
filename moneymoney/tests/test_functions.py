
from moneymoney import models, functions
@functions.suppress_stdout
def test_print_object(self):
    b=models.Banks()
    b.name="Newbank"
    b.save()
    functions.print_object(b)
    

def test_string_oneline_object(self):
    b=models.Banks()
    b.name="Newbank"
    b.save()
    assert len(functions.string_oneline_object(b))>0

def test_have_different_sign(self):
    assert functions.have_different_sign(1, 1)==False
    assert functions.have_different_sign(1, -1)==True
    assert functions.have_different_sign(-1, 1)==True
    assert functions.have_different_sign(-1, -1)==False
    assert functions.have_different_sign(0, 1)==True
    assert functions.have_different_sign(-1, 0)==True
    assert functions.have_different_sign(0, 0)==True        
