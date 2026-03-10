const stateCityData = {
    "Karnataka": ["Bangalore", "Mysore", "Mangalore", "Hubli"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "Kerala": ["Kochi", "Trivandrum", "Kozhikode"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
    "Andhra Pradesh": ["Vijayawada", "Guntur", "Visakhapatnam"]
};

const stateSelect = document.getElementById("state");
const citySelect = document.getElementById("city");

/* Load states */
document.addEventListener("DOMContentLoaded", () => {
    // Load states on page load
    print_state("state");

    // When state changes → load cities
    document.getElementById("state").addEventListener("change", function () {
        const stateIndex = this.selectedIndex;
        if (stateIndex > 0) {
            print_city("city", stateIndex);
        } else {
            document.getElementById("city").length = 1;
        }
    });
});
