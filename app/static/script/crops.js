const crops = [
"Rice", "Wheat", "Maize", "Barley", "Jowar", "Bajra", "Ragi", "Chickpea", 
"Pigeon pea", "Green gram", "Black gram", "Lentil", "Peas", "Cowpea", "Groundnut", 
"Mustard", "Soybean", "Sunflower", "Sesame", "Safflower", "Linseed", "Castor", 
"Coconut", "Sugarcane", "Sugar beet", "Sweet potato", "Cotton", "Jute", "Flax", 
"Hemp", "Tea", "Coffee", "Rubber", "Arecanut", "Cocoa", "Black pepper", "Cardamom", 
"Clove", "Cinnamon", "Nutmeg", "Turmeric", "Ginger", "Chilli", "Coriander", "Cumin", 
"Fennel", "Fenugreek", "Potato", "Tomato", "Onion", "Brinjal", "Cabbage", "Cauliflower", 
"Okra", "Spinach", "Carrot", "Radish", "Beans", "Mango", "Banana", "Apple", "Orange", 
"Grapes", "Guava", "Papaya", "Pineapple", "Pomegranate", "Watermelon", "Muskmelon", 
"Tapioca", "Yam", "Beetroot", "Berseem", "Alfalfa", "Napier grass", "Fodder maize", 
"Fodder sorghum", "Tulsi", "Neem", "Aloe vera", "Ashwagandha", "Mint", "Lemongrass"
];

const cropSelect = document.getElementById("crop");

crops.forEach(crop => {
    let option = document.createElement("option");
    option.value = crop.toLowerCase();
    option.textContent = crop.toUpperCase();
    cropSelect.appendChild(option);
});
