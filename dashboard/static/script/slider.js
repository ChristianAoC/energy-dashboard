/*
From:
https://medium.com/@predragdavidovic10/native-dual-range-slider-html-css-javascript-91e778134816
*/

let colorOne = "#C6C6C6";
let colorTwo = "#222222";

function controlFromInput(fromSlider, fromInput, toInput, controlSlider) {
    const [from, to] = getParsed(fromInput, toInput);
    fillSlider(fromInput, toInput, colorOne, colorTwo, controlSlider);
    if (from > to) {
        fromSlider.value = to;
        fromInput.value = to;
    } else {
        fromSlider.value = from;
    }
  localStorage.setItem(fromSlider.id, fromSlider.value);
}
    
function controlToInput(toSlider, fromInput, toInput, controlSlider) {
    const [from, to] = getParsed(fromInput, toInput);
    fillSlider(fromInput, toInput, colorOne, colorTwo, controlSlider);
    setToggleAccessible(toInput);
    if (from <= to) {
        toSlider.value = to;
        toInput.value = to;
    } else {
        toInput.value = from;
    }
  localStorage.setItem(toSlider.id, toSlider.value);
}

function controlFromSlider(fromSlider, toSlider, fromInput) {
  sliderChange();
  const [from, to] = getParsed(fromSlider, toSlider);
  fillSlider(fromSlider, toSlider, colorOne, colorTwo, toSlider);
  if (from > to) {
    fromSlider.value = to;
    fromInput.value = to;
  } else {
    fromInput.value = from;
  }
  localStorage.setItem(fromSlider.id, fromSlider.value);
}

function controlToSlider(fromSlider, toSlider, toInput) {
  sliderChange();
  const [from, to] = getParsed(fromSlider, toSlider);
  fillSlider(fromSlider, toSlider, colorOne, colorTwo, toSlider);
  setToggleAccessible(toSlider);
  if (from <= to) {
    toSlider.value = to;
    toInput.value = to;
  } else {
    toInput.value = from;
    toSlider.value = from;
  }
  localStorage.setItem(toSlider.id, toSlider.value);
}

function getParsed(currentFrom, currentTo) {
  const from = parseInt(currentFrom.value, 10);
  const to = parseInt(currentTo.value, 10);
  //localStorage.setItem(currentFrom.id, currentFrom.value);
  //localStorage.setItem(currentTo.id, currentTo.value);
  return [from, to];
}

function fillSlider(from, to, sliderColor, rangeColor, controlSlider) {
    const rangeDistance = to.max-to.min;
    const fromPosition = from.value - to.min;
    const toPosition = to.value - to.min;
    controlSlider.style.background = `linear-gradient(
      to right,
      ${sliderColor} 0%,
      ${sliderColor} ${(fromPosition)/(rangeDistance)*100}%,
      ${rangeColor} ${((fromPosition)/(rangeDistance))*100}%,
      ${rangeColor} ${(toPosition)/(rangeDistance)*100}%, 
      ${sliderColor} ${(toPosition)/(rangeDistance)*100}%, 
      ${sliderColor} 100%)`;
}

function setToggleAccessible(currentTarget) {
  const toSlider = document.querySelector('#'+currentTarget.id);
  if (Number(currentTarget.value) <= 0 ) {
    toSlider.style.zIndex = 5;
  } else {
    toSlider.style.zIndex = 2;
  }
}

function initiateSliders(knob, index) {
	if (localStorage.getItem(knob.id) === null) {
		knob.value = allInitValues[index];
	} else {
		knob.value = localStorage.getItem(knob.id);
	}
	knob.dispatchEvent(new Event('input'));
}

$(document).ready( function () {
    const fromSlider1 = document.querySelector('#fromSlider1');
    const toSlider1 = document.querySelector('#toSlider1');
    const fromInput1 = document.querySelector('#fromInput1');
    const toInput1 = document.querySelector('#toInput1');
    setToggleAccessible(toSlider1);
    
    fromSlider1.oninput = () => controlFromSlider(fromSlider1, toSlider1, fromInput1);
    toSlider1.oninput = () => controlToSlider(fromSlider1, toSlider1, toInput1);
    fromInput1.oninput = () => controlFromInput(fromSlider1, fromInput1, toInput1, toSlider1);
    toInput1.oninput = () => controlToInput(toSlider1, fromInput1, toInput1, toSlider1);
    
    const fromSlider2 = document.querySelector('#fromSlider2');
    const toSlider2 = document.querySelector('#toSlider2');
    const fromInput2 = document.querySelector('#fromInput2');
    const toInput2 = document.querySelector('#toInput2');
    setToggleAccessible(toSlider2);
    
    fromSlider2.oninput = () => controlFromSlider(fromSlider2, toSlider2, fromInput2);
    toSlider2.oninput = () => controlToSlider(fromSlider2, toSlider2, toInput2);
    fromInput2.oninput = () => controlFromInput(fromSlider2, fromInput2, toInput2, toSlider2);
    toInput2.oninput = () => controlToInput(toSlider2, fromInput2, toInput2, toSlider2);
    
    const fromSlider3 = document.querySelector('#fromSlider3');
    const toSlider3 = document.querySelector('#toSlider3');
    const fromInput3 = document.querySelector('#fromInput3');
    const toInput3 = document.querySelector('#toInput3');
    setToggleAccessible(toSlider3);
    
    fromSlider3.oninput = () => controlFromSlider(fromSlider3, toSlider3, fromInput3);
    toSlider3.oninput = () => controlToSlider(fromSlider3, toSlider3, toInput3);
    fromInput3.oninput = () => controlFromInput(fromSlider3, fromInput3, toInput3, toSlider3);
    toInput3.oninput = () => controlToInput(toSlider3, fromInput3, toInput3, toSlider3);
    
    // set initial values, after that get from local storage, and trigger input events to redraw
    
    let allSliderKnobs = [fromSlider1, fromSlider2, fromSlider3, toSlider1, toSlider2, toSlider3];
    let allInitValues = [0, 0, 0, 99999, 99999, 99999];

    //allSliderKnobs.forEach(initiateSliders);

    fillSlider(fromSlider1, toSlider1, colorOne, colorTwo, toSlider1);
    fillSlider(fromSlider2, toSlider2, colorOne, colorTwo, toSlider2);
    fillSlider(fromSlider3, toSlider3, colorOne, colorTwo, toSlider3);
});
