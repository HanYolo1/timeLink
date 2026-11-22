"""A program variant is reused only while its translation's texture questions are answered the same (#29).

Two translations of Zora's River's waterfall program both fitted the textures of its single descriptors: one made in play, and
one a pipeline state list gave its questions to in order, which answered one of them the other way. Whichever the program's list
had first was drawn, and the waterfalls came out flat brown. The translation now notes where each question's handle came from
(Program::question_at, by Environment::NextTextureQuestionAt), and still_valid asks each again of the texture there.

questions_fit and the count it keeps are cut out of gpu/vk/vk_shader.cpp and compiled with the real Program and Stage, the
banks' words and the textures' types stood in. Checked: a question answered the same fits; another answer turns the variant
down and is counted; of two variants alike but for one answer, only the one the textures answer fits; a handle made of two words
is read as the translator reads it (GetTextureHandle); an integer question; a question whose place is not known, or whose stage
the program has not, is passed over; RX_VK_VARIANT_QUESTIONS=0 takes the answers alone, as before. And in the sources: every
texture question the translator asks names its place first, the environment notes it with the answer used, and a program
record keeps them (kProgramCacheFormat raised).

python -I -B tests/test_variant_questions.py --headers <Vulkan-Headers/include> [--cxx clang++]
"""
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import os
import subprocess
import tempfile
from pathlib import Path

RUN_ALL_ARGS = ["--cxx", "clang++", "--headers", "{vulkan_headers}"]

ROOT = Path(__file__).resolve().parents[1]
ENV_ON_H = str(ROOT / "gpu" / "vk" / "compat" / "timeLink_env.h")


def block(text, marker):
    start = text.index(marker)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


FIXTURE = r"""
// SPDX-License-Identifier: GPL-3.0-or-later
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <map>
#include "vk_shader.h"
namespace mkwvk {
static std::map<std::pair<uint32_t, uint32_t>, uint32_t> words;   // (bank, offset) -> word, the draw's banks
static std::map<uint32_t, uint8_t> types;                          // handle -> Shader::TextureType
static std::map<uint32_t, bool> integer;
static int reads_stage = -1;
uint32_t stage_cbuf_word(const NvnState&, const Stage& st, uint32_t index, uint32_t offset) {
    reads_stage = st.nvn_stage;
    const auto it = words.find({index, offset});
    return it == words.end() ? 0 : it->second;
}
Shader::TextureType handle_texture_type(uint32_t h) {
    const auto it = types.find(h);
    return (Shader::TextureType)(it == types.end() ? 2 : it->second);
}
bool handle_is_integer(uint32_t h) { return integer.count(h) && integer[h]; }
void logf(const char*, ...) {}
#include QUESTIONS_FIT
}
using namespace mkwvk;
static int failed = 0;
#define WANT(c) do { if (!(c)) std::printf("FAIL: %s (line %d)\n", #c, __LINE__), failed++; } while (0)
static Program::QuestionAt at(uint8_t index, uint32_t offset, uint8_t kind, uint8_t answer) {
    Program::QuestionAt q{};
    q.index = index, q.offset = offset, q.nvn_stage = 1, q.kind = kind, q.answer = answer;
    return q;
}
static std::unique_ptr<Program> program(std::vector<Program::QuestionAt> qs) {
    auto p = std::make_unique<Program>();
    p->stages.emplace_back();
    p->stages[0].nvn_stage = 1;   // (the fragment stage)
    p->question_at = std::move(qs);
    return p;
}
int main(int argc, char** argv) {
    auto s = std::make_unique<NvnState>();
    const bool off = argc > 1;
    words[{2, 0x10}] = 5;
    types[5] = 2;   // (Color2D)
    auto same = program({at(2, 0x10, 0, 2)});
    WANT(questions_fit(*s, *same));
    WANT(off ? reads_stage == -1 : reads_stage == 1);   // (off: nothing is read again)
    types[5] = 0;   // (Color1D now: the question is answered the other way)
    const int64_t before = questions_turned_down.load();
    WANT(questions_fit(*s, *same) == off);
    WANT(questions_turned_down.load() - before == (off ? 0 : 1));
    // (#29: two variants alike but for one answer; the textures there answer 0)
    auto list_made = program({at(2, 0x18, 0, 2), at(2, 0x10, 0, 2)});
    auto play_made = program({at(2, 0x18, 0, 2), at(2, 0x10, 0, 0)});
    WANT(questions_fit(*s, *list_made) == off);
    WANT(questions_fit(*s, *play_made));
    // (a handle of two words: word(index, offset) << shift | word(secondary) << secondary shift, as GetTextureHandle)
    words[{2, 0x40}] = 0x0007, words[{3, 0x80}] = 0x0003;
    types[0x0007 | (0x0003 << 20)] = 3;   // (ColorArray2D)
    auto two = program({at(2, 0x40, 0, 3)});
    two->question_at[0].has_secondary = 1, two->question_at[0].secondary_index = 3, two->question_at[0].secondary_offset = 0x80;
    two->question_at[0].secondary_shift_left = 20;
    WANT(questions_fit(*s, *two));
    two->question_at[0].secondary_offset = 0x84;   // (another word there: another handle, another type)
    WANT(questions_fit(*s, *two) == off);
    // (one word: the handle is that word, or'd with itself shifted by the secondary shift, 0 here)
    auto one = program({at(2, 0x40, 0, 2)});
    WANT(questions_fit(*s, *one));
    // (whether the format is integer)
    integer[5] = true;
    auto asks_int = program({at(2, 0x10, 1, 1)});
    WANT(questions_fit(*s, *asks_int));
    integer[5] = false;
    WANT(questions_fit(*s, *asks_int) == off);
    // (passed over: a place not known, a stage the program has not; and no questions at all)
    auto unknown = program({at(0xFF, 0x10, 0, 7)});
    WANT(questions_fit(*s, *unknown));
    auto other_stage = program({at(2, 0x10, 0, 7)});
    other_stage->question_at[0].nvn_stage = 0;
    WANT(questions_fit(*s, *other_stage));
    WANT(questions_fit(*s, *program({})));
    std::printf("%s: %s\n", off ? "RX_VK_VARIANT_QUESTIONS=0" : "default", failed ? "failed" : "ok");
    return failed ? 1 : 0;
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="clang++")
    parser.add_argument("--headers", type=Path, required=True)
    args = parser.parse_args()
    vk = ROOT / "gpu" / "vk"
    shader = (vk / "vk_shader.cpp").read_text(encoding="utf-8")
    problems = []
    if "bool questions_fit(" not in shader:
        raise SystemExit("FAIL: vk_shader.cpp has no questions_fit: a variant is reused on its single descriptors' answers alone (#29)")
    # (the sources: every question names its place first, the environment notes it, still_valid asks, and records keep them)
    texture_pass = (vk / "eden/shader_recompiler/ir_opt/texture_pass.cpp").read_text(encoding="utf-8")
    for asked in ("env.ReadTextureType(", "env.IsTexturePixelFormatInteger("):
        at = 0
        while (at := texture_pass.find(asked, at)) >= 0:
            before = texture_pass[texture_pass.rfind("\n", 0, texture_pass.rfind("\n", 0, at)):at]
            if "env.NextTextureQuestionAt(cbuf);" not in before:
                problems.append("texture_pass.cpp asks %s without naming its place on the line before" % asked)
            at += len(asked)
    environment = (vk / "eden/shader_recompiler/environment.h").read_text(encoding="utf-8")
    if "virtual void NextTextureQuestionAt(const ConstBufferAddr&) {}" not in environment:
        problems.append("Environment has no NextTextureQuestionAt that does nothing by default")
    env = block(shader, "class Env final : public Shader::Environment")
    if "void NextTextureQuestionAt(const Shader::ConstBufferAddr& a) override" not in env or "question_at_out->push_back(q);" not in env:
        problems.append("the translation's environment does not note each question's place with its answer")
    if "return questions_fit(s, p);" not in block(shader, "bool still_valid("):
        problems.append("still_valid does not ask the questions again")
    if "question_at_out = &p.question_at;" not in block(shader, "struct QuestionsNoted"):
        problems.append("a translation does not note its questions' places into its program")
    cache = (vk / "vk_progcache.cpp").read_text(encoding="utf-8")
    if "put_list(o, p.question_at);" not in block(cache, "void put_head(") or "r.list(p.question_at);" not in block(cache, "void get_head("):
        problems.append("a program record does not keep its questions' places")
    if "constexpr uint32_t kProgramCacheFormat = 1;" in cache:
        problems.append("kProgramCacheFormat not raised for the records' new field")
    for p in problems:
        print("FAIL:", p)
    counted = shader[shader.rfind("\n", 0, shader.index("questions_turned_down{")) + 1:]
    functions = counted[:counted.index(";") + 1] + "\n\n" + block(shader, "bool questions_fit(")
    flags = ["-std=c++20", "-include", ENV_ON_H, "-O1", "-w", "-DNDEBUG", "-DVK_NO_PROTOTYPES", "-DMKWVK_INCLUDES=2"]
    for header in ("algorithm", "cstdio", "cstdlib", "cstring", "functional", "string", "vector"):
        flags += ["-include", header]
    includes = [vk, vk / "compat", ROOT / "gpu/compat", vk / "eden", ROOT / "gpu/third_party/suyu", args.headers]
    if os.name != "nt":
        includes.insert(0, ROOT / "host/posix")
    flags += ["-I" + str(Path(p).resolve()) for p in includes]
    failed = bool(problems)
    with tempfile.TemporaryDirectory(prefix="variant-questions-") as temp:
        folder = Path(temp)
        cpp, exe = folder / "fixture.cpp", folder / "fixture.exe"
        cpp.write_text(FIXTURE.replace("#include QUESTIONS_FIT", functions), encoding="utf-8")
        subprocess.run([args.cxx, *flags, str(cpp), "-o", str(exe)], cwd=folder, check=True)
        for off in (False, True):   # (each run reads the switch once, as questions_fit does)
            env_vars = dict(os.environ)
            env_vars.pop("RX_VK_VARIANT_QUESTIONS", None)
            if off:
                env_vars["RX_VK_VARIANT_QUESTIONS"] = "0"
            failed |= subprocess.run([str(exe)] + (["off"] if off else []), cwd=folder, env=env_vars).returncode != 0
    if failed:
        raise SystemExit(1)
    print("PASS: a variant is reused only while its texture questions are answered the same")


if __name__ == "__main__":
    main()
