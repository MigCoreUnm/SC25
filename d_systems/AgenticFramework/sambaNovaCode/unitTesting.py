# Import necessary modules and classes
from AgenticFramework.AgenticSystem import AgenticSystem, Node
from dotenv import load_dotenv
from sambaNovaCode.myTools import run_c, run_py, run_fortran, embeddingDataSet  # Ensure myTools.py contains the defined tools
from datasets import load_dataset

load_dotenv()

ds = load_dataset("HPC-Forran2Cpp/HPC_Fortran_CPP")
ds = ds['test']
documents = []
vector_store = embeddingDataSet()

for x in range(0, len(ds)):
    cpp = ds[x].get('cpp', '')
    fortran = ds[x].get('fortran', '')
    page_content = f"CPP Code:\n{cpp}\n\nFortran Code:\n{fortran}"
    documents.append(page_content)

vector_store.init_database(documents=documents)

fort = """
program calculate_sum
    implicit none
    integer :: num1, num2, result

    ! Initialize the numbers
    num1 = 2
    num2 = 1
problem with genrating tests

    ! Call the function to calculate the sum
    result = calculateSum(num1, num2)

    ! Print the result
    print *, "The sum is: ", result
end program calculate_sum

! Function to calculate the sum of two numbers
function calculateSum(a, b) result(sum)
    implicit none
    integer, intent(in) :: a, b
    integer :: sum

    sum = a + b
end function calculateSum
"""

c = """
#include <iostream>
using namespace std;

int main() {
    const int n = 5;
    int arr[n];
    int i, j, temp;

    // Prompt user to enter n integers
    cout << "Enter " << n << " integers:" << endl;
    for (i = 0; i < n; i++) {
        cin >> arr[i];
    }

    // Bubble sort algorithm
    // Note: C++ arrays are 0-indexed, unlike Fortran which starts at 1.
    for (i = 0; i < n - 1; i++) {
        for (j = 0; j < n - 1 - i; j++) {
            if (arr[j] > arr[j+1]) {
                temp = arr[j];
                arr[j] = arr[j+1];
                arr[j+1] = temp;
            }
        }
    }

    // Print the sorted array
    cout << "Sorted array:" << endl;
    for (i = 0; i < n; i++) {
        cout << arr[i] << endl;
    }

    return 0;
}
"""

system = AgenticSystem()

# Define Node 1: Translation from Fortran to C++
node1_instruction ="Your role is to take in Fortran code and output the C++ translation. "
"The output is only the code, no comments or explanations, and can be run within a file immediately. "
f"\n\n Example:\nfortran: {fort}\n C++: {c}"

# Define Node 2: Compile and Run C++ Code

node2_instructions = "Your role is to compile and run the given C++ code. "
"If there are compilation or runtime errors, return only the error messages. "
"Do not provide any additional commentary or explanation."


# Define Node 3: Compile and Run Fortran Code
node3_instruction ="Your role is to compile and run the given Fortran code. "
"If there are compilation or runtime errors, return only the error messages. "
"Do not provide any additional commentary or explanation."


# Define Node 4: Generate Unit Tests (Depends on both C++ and Fortran Execution Results)
node4_instruction ="Your role is to generate unit tests for the given functions in both C++ and Fortran."
"The resulting output must be only the test code, with no additional comments or explanations, "
"and must compile and run immediately. The tests should be self-contained, have no external dependencies,"
"and print clear pass/fail messages (e.g., 'Test Passed', 'Test Failed'). ",
"Ensure there are no bugs or compilation issues."

# Define Node 5: Evaluate Translation Quality (End Node)
node5_instruction ="""Your role is to evaluate the quality of the translation from Fortran to C++\n
Provide a rating based on the following metrics: cleanliness, accuracy, efficiency, memory usage. on a scale of one to ten\n
\n\n example output:\n\n ,
cleanliness: 9\n accuracy: 7\n efficieny: 6\n memory usage: 5\n your output must be a rating in the above format \n \n  """
# Add nodes to the AgenticSystem with multiple input dependencies
system.add_node(
    instructions=node1_instruction,
    cot="", 
    name="translation_node1",
    tool_caller=False,
    tools=None,
    inputNodes=None,  
    is_end_node=False
)

system.add_node(
    instructions=node2_instructions,
    cot="",
    name="execution_node2",
    tool_caller=True,
    tools=[run_c],
    inputNodes=["translation_node1"],  
    is_end_node=False
)


system.add_node(
    instructions=node3_instruction,
    cot="",
    name="execution_node3",
    tool_caller=True,
    tools=[run_fortran],
    inputNodes=["translation_node1"],  
    is_end_node=False
)

system.add_node(
    instructions=node4_instruction,
    cot="",
    name="unit_test_node4",
    tool_caller=False,  
    tools=None,
    inputNodes=["execution_node2", "execution_node3"], 
    is_end_node=False
)

system.add_node(
    instructions=(
        "Your role is to compile and execute the given C++ unit tests. "
        "Return the test results, indicating whether each test passed or failed."
    ),
    cot="",
    name="execution_node4",  
    tool_caller=True,
    tools=[run_c],
    inputNodes=["unit_test_node4"],
    is_end_node=False
)

system.add_node(
    instructions=(
        "Your role is to compile and execute the given Fortran unit tests. "
        "Return the test results, indicating whether each test passed or failed."
    ),
    cot="",
    name="execution_node5",  
    tool_caller=True,
    tools=[run_fortran],
    inputNodes=["unit_test_node4"],  
    is_end_node=False
)

system.add_node(
    instructions=node5_instruction,
    cot="",
    name="evaluation_node5",
    tool_caller=False,
    tools=None,
    inputNodes=["all"],  
    is_end_node=True
)

system.add_edge("translation_node1", "execution_node2")  # Translate -> Execute C++
system.add_edge("translation_node1", "execution_node3")  # Translate -> Execute Fortran
system.add_edge("execution_node2", "unit_test_node4")    # Execute C++ -> Generate Unit Tests
system.add_edge("execution_node3", "unit_test_node4")    # Execute Fortran -> Generate Unit Tests
system.add_edge("unit_test_node4", "execution_node4")    # Generate Unit Tests -> Execute C++ Tests
system.add_edge("unit_test_node4", "execution_node5")    # Generate Unit Tests -> Execute Fortran Tests
system.add_edge("execution_node4", "evaluation_node5")   # Execute C++ Tests -> Evaluate
system.add_edge("execution_node5", "evaluation_node5")   # Execute Fortran Tests -> Evaluate


system.define_start("translation_node1")

# Define the Fortran code 
fortran_code = """
program calculate_sum
    implicit none
    integer :: num1, num2, result

    ! Initialize the numbers
    num1 = 2
    num2 = 1

    ! Call the function to calculate the sum
    result = calculateSum(num1, num2)

    ! Print the result
    print *, "The sum is: ", result
end program calculate_sum

! Function to calculate the sum of two numbers
function calculateSum(a, b) result(sum)
    implicit none
    integer, intent(in) :: a, b
    integer :: sum

    sum = a + b
end function calculateSum
"""

# Perform vector search to retrieve related code snippets for context
related_code = vector_store.vector_search(fortran_code)
related_code = (
    "This code gives some examples of translation from Fortran to C++:\n\n" 
    + related_code 
    + "\n\nThis is the code to translate:\n\n" 
    + fortran_code
)

final_answer = system.generate_answer(related_code)

system.print_system_state()

print("Final Evaluation:", final_answer.content)
