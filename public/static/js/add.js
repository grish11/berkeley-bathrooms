/* The "Extra photos" picker on the /add form.
 *
 * The problem this solves: a <input type="file" multiple> REPLACES its whole
 * selection every time the picker is opened. Pick two photos, then open the
 * picker again to grab a third from another folder, and the first two are
 * silently gone. There is also nothing on the page saying what is selected,
 * so you only find out after submitting.
 *
 * So this keeps its own list of chosen files, adds to it on every pick, and
 * writes the list back onto the input before submit. Assigning input.files
 * needs a DataTransfer -- a FileList cannot be built any other way:
 * https://developer.mozilla.org/en-US/docs/Web/API/DataTransfer
 * https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/files
 */

const input = document.getElementById("extra_photos");
const list = document.getElementById("extra-photos-list");

// The files we intend to upload, across however many trips to the picker.
let chosen = [];

input.addEventListener("change", () => {
  for (const file of input.files) {
    // Same name and size twice means the same photo picked twice -- most
    // likely the same folder reopened, not two different shots.
    const duplicate = chosen.some(
      (c) => c.name === file.name && c.size === file.size,
    );
    if (!duplicate) chosen.push(file);
  }
  sync();
});

/** Copy `chosen` onto the input, then redraw the list under it. */
function sync() {
  const transfer = new DataTransfer();
  for (const file of chosen) transfer.items.add(file);
  // Assigning .files does NOT fire another change event, so this cannot loop.
  input.files = transfer.files;
  render();
}

/** Show what is selected, with a way to drop any one of them. */
function render() {
  list.replaceChildren();

  for (const [index, file] of chosen.entries()) {
    const item = document.createElement("li");

    const name = document.createElement("span");
    name.className = "chosen-name";
    name.textContent = file.name;
    item.append(name);

    const size = document.createElement("span");
    size.className = "chosen-size";
    size.textContent = `${Math.round(file.size / 1024)} KB`;
    item.append(size);

    const remove = document.createElement("button");
    // Inside a <form>, a button with no type is a SUBMIT button -- without
    // this, clicking "remove" would submit the half-filled form.
    remove.type = "button";
    remove.className = "chosen-remove";
    remove.textContent = "remove";
    remove.title = `Remove ${file.name}`;
    remove.addEventListener("click", () => {
      chosen.splice(index, 1);
      sync();
    });
    item.append(remove);

    list.append(item);
  }
}
