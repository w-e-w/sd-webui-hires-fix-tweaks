function setInputToValueHrTweaks(elem_id, value) {
    const input = gradioApp().querySelector("#" + elem_id + " input");
    input.value = value;
    updateInput(input);
}