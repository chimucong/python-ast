import ast
import astunparse


class StatInit(ast.NodeVisitor):
    attr_set = set()

    def visit_FunctionDef(self, node):
        if node.name == '__init__':
            self.generic_visit(node)

    def visit_Assign(self, node):
        for t in node.targets:
            self.attr_set.add(t.attr)
        return


class ReWriteInit(ast.NodeTransformer):
    def __init__(self, call_list, transform_map):
        super().__init__()
        self.call_list = call_list
        self.transform_map = transform_map

    def visit_FunctionDef(self, node):
        if node.name == '__init__':
            for (attr, count) in self.call_list:
                assign = self.generate_assign(attr, count)
                node.body.append(assign)
        return node

    def generate_assign(self, attr, count):
        assign = ast.parse(self.transform_map.get(attr)).body[0]
        assign.targets[0].attr = attr + str(count)
        return assign


class RewriteForward(ast.NodeTransformer):

    def __init__(self, attr_count):
        super().__init__()
        self.attr_count = attr_count
        self.call_list = []

    def visit_FunctionDef(self, node):
        if node.name == 'forward':
            self.generic_visit(node)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if node.func.value.id == 'F':
            attr = node.func.attr

            count = self.attr_count.get(attr, 0)+1
            self.attr_count[attr] = count

            node.func.value.id = 'self'
            node.func.attr = attr + str(count)

            self.call_list.append((attr, count))
        return node


myclass = '''
class Net(nn.Module):
    def __init__(self):
        self.conv2 = nn.Conv2d(20, 50.5, 1)
        self.fc1 = nn.Liner(4*4*50, 500)
        self.fc2 = nn.Linear(500, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 4*4*50)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x
'''

transform_map = {
    'relu': 'self.relu = nn.ReLU()',
    'max_pool2d': 'self.max_pool2d = lambda x, y, z: nn.MaxPool2d((y,z))(x)'
}

node = ast.parse(myclass)
statInit = StatInit()
statInit.visit(node)
attr_count = {}
for itr in statInit.attr_set:
    attr_count[itr] = 1

rewriteForward = RewriteForward(attr_count)
node = rewriteForward.visit(node)

rewriteInit = ReWriteInit(rewriteForward.call_list, transform_map)
node = rewriteInit.visit(node)


print(myclass)
print('------------')
print('Transformed:')
print('------------')

print(astunparse.unparse(node))

