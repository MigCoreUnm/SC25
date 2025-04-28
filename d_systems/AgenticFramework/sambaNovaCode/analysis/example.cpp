#include <iostream>
using namespace std;

int main() {
    double radius, area;
    const double pi = 3.14159;
    radius = 5.0;
    area = pi * radius * radius;
    cout << "For a circle with radius " << radius << " the area is " << area << endl;
    // Removed division by zero error
    // int x = 5 / 0; // This line has been removed to prevent runtime error
    return 0;
}