export function checkDockingTool(element) {
    // checkbox 하나만 작동하도록 설정
    const checkboxes = document.getElementsByName("docking");

    checkboxes.forEach((cb) => {
        if (cb !== element) {
            cb.checked = false;
        }
    });

    element.checked = true;

    // Haddock3 옵션 구성 위한 입력창 생성
    const formContainer = element.closest("form");
    const haddockInput = document.getElementById("haddock-input");
    const haddockBS = document.getElementById("haddock-bs");
    const haddockAntigen = document.getElementById("haddock-antigen");
    const haddockNanobody = document.getElementById("haddock-nanobody");
    const haddockDecoy = document.getElementById("haddock-decoy");
    const haddockBreak = document.getElementById("haddock-break");

    if (element.value === "haddock") {
        if (!haddockInput) {
            const newRow1 = document.createElement("div");
            newRow1.setAttribute("id", "haddock-input");
            newRow1.style.marginTop = "20px";
            newRow1.innerHTML = `
                <h3 style="text-align: center; color: #219ebc; font-size: 20px;">Haddock3 Options</h3>
            `;
            const newRow2 = document.createElement("div");
            newRow2.setAttribute("id", "haddock-bs");
            newRow2.innerHTML = `
                <div class="form-group">
                    <label style="width: 100%;">Binding Sites (optional, e.g. 122 123 124)</label>
                </div>
            `;
            const newRow3 = document.createElement("div");
            newRow3.setAttribute("id", "haddock-antigen");
            newRow3.innerHTML = `
                <div class="form-group">
                    <label>Antigen Active residue No.</label>
                    <input type="text" name="antigen_act" class="input-field">
                </div>
            `;
            const newRow4 = document.createElement("div");
            newRow4.setAttribute("id", "haddock-nanobody");
            newRow4.innerHTML = `
                <div class="form-group">
                    <label>Nanobody Passive residue No.</label>
                    <input type="text" name="nanobody_pass" class="input-field">
                </div>
            `;
            const newRow5 = document.createElement("div");
            newRow5.setAttribute("id", "haddock-decoy");
            newRow5.innerHTML = `
                <div class="form-group">
                    <label># of Decoy</label>
                    <input type="text" name="decoy" class="input-field">
                </div>
            `;
            const newRow6 = document.createElement("div");
            newRow6.setAttribute("id", "haddock-break");
            newRow6.innerHTML = `<br>`;

            formContainer.appendChild(newRow1);
            formContainer.appendChild(newRow2);
            formContainer.appendChild(newRow3);
            formContainer.appendChild(newRow4);
            formContainer.appendChild(newRow5);
            formContainer.appendChild(newRow6);
        }
    } else {
        // Haddock3 옵션이 아닌 경우 생성된 요소들 제거
        if (haddockInput) haddockInput.remove();
        if (haddockBS) haddockBS.remove();
        if (haddockAntigen) haddockAntigen.remove();
        if (haddockNanobody) haddockNanobody.remove();
        if (haddockDecoy) haddockDecoy.remove();
        if (haddockBreak) haddockBreak.remove();
    }
}