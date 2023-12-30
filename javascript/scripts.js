function setInputToValue(elem_id, value) {
    var input = gradioApp().querySelector("#" + elem_id + " input");
    if (!input) return [];

    input.value = value;
    updateInput(input);
    return [];
}