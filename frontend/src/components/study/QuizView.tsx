import React, { useState, useEffect } from "react";
import { DocumentMetadata, QuizResponse, QuizQuestion, QuizEvaluationResponse } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import {
  Award,
  CheckCircle2,
  XCircle,
  RotateCcw,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Target,
} from "lucide-react";

interface QuizViewProps {
  document: DocumentMetadata | null;
  initialTopic?: string | null;
}

export const QuizView: React.FC<QuizViewProps> = ({ document, initialTopic }) => {
  const [data, setData] = useState<QuizResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Quiz state
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isAnswerSubmitted, setIsAnswerSubmitted] = useState(false);
  const [userAnswers, setUserAnswers] = useState<
    { question_id: number; user_answer: string; topic: string }[]
  >([]);
  const [isQuizComplete, setIsQuizComplete] = useState(false);
  const [evaluation, setEvaluation] = useState<QuizEvaluationResponse | null>(null);

  // Config state
  const [numQuestions, setNumQuestions] = useState(10);
  const [focusedTopic] = useState<string | null>(initialTopic || null);

  const fetchQuiz = async (forceRegenerate = false) => {
    if (!document || document.status !== "ready") return;
    setIsLoading(true);
    setError(null);
    setCurrentIndex(0);
    setSelectedOption(null);
    setIsAnswerSubmitted(false);
    setUserAnswers([]);
    setIsQuizComplete(false);
    setEvaluation(null);

    try {
      const res = await api.getQuiz(
        document.document_id,
        numQuestions,
        focusedTopic || undefined,
        forceRegenerate
      );
      setData(res);
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.message
          : "We couldn't generate a quiz for this document. Please try again.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    if (!document || document.status !== "ready") {
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setError(null);
      setCurrentIndex(0);
      setSelectedOption(null);
      setIsAnswerSubmitted(false);
      setUserAnswers([]);
      setIsQuizComplete(false);
      setEvaluation(null);
      try {
        const res = await api.getQuiz(
          document.document_id,
          numQuestions,
          focusedTopic || undefined,
          false
        );
        if (isMounted) setData(res);
      } catch (err: unknown) {
        if (isMounted) {
          const msg =
            err instanceof ApiError
              ? err.message
              : "We couldn't generate a quiz for this document. Please try again.";
          setError(msg);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    load();
    return () => {
      isMounted = false;
    };
  }, [document?.document_id, document?.status, focusedTopic, numQuestions]);

  const currentQuestion: QuizQuestion | undefined = data?.questions[currentIndex];

  const handleSubmitAnswer = () => {
    if (!selectedOption || !currentQuestion || isAnswerSubmitted) return;

    setIsAnswerSubmitted(true);
    const newAnswer = {
      question_id: currentQuestion.id,
      user_answer: selectedOption,
      topic: currentQuestion.topic,
    };
    const updated = [...userAnswers, newAnswer];
    setUserAnswers(updated);
  };

  const handleNextQuestion = async () => {
    if (!data) return;

    if (currentIndex + 1 < data.questions.length) {
      setCurrentIndex((prev) => prev + 1);
      setSelectedOption(null);
      setIsAnswerSubmitted(false);
    } else {
      setIsQuizComplete(true);
      try {
        const evalRes = await api.evaluateQuiz(
          document!.document_id,
          userAnswers,
          data.questions
        );
        setEvaluation(evalRes);
      } catch {
        const score = userAnswers.filter((a) => {
          const q = data.questions.find((quest) => quest.id === a.question_id);
          return q && a.user_answer.trim().toLowerCase() === q.correct_answer.trim().toLowerCase();
        }).length;
        setEvaluation({
          score,
          total: data.questions.length,
          accuracy_percentage: Math.round((score / data.questions.length) * 100),
          weak_topics: [],
          recommendations: ["Review incorrect questions below."],
        });
      }
    }
  };

  const handleRetake = () => {
    setCurrentIndex(0);
    setSelectedOption(null);
    setIsAnswerSubmitted(false);
    setUserAnswers([]);
    setIsQuizComplete(false);
    setEvaluation(null);
  };

  if (!document || document.status !== "ready") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto animate-fade-in">
        <div className="w-12 h-12 rounded-2xl bg-zinc-100 text-zinc-500 border border-zinc-200 flex items-center justify-center mb-3">
          <Award className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-black">
          AI Quiz Generator
        </h3>
        <p className="text-xs text-zinc-500 mt-1">
          Upload and index an academic PDF to generate interactive, grounded multiple-choice questions with weak-topic analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 max-w-3xl mx-auto w-full animate-fade-in">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-5 mb-6 border-b border-zinc-200">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-black tracking-tight flex items-center gap-2">
              <Award className="w-5 h-5 text-black" />
              Interactive AI Quiz
            </span>
            {data?.cached && (
              <span className="text-[10px] font-mono bg-zinc-100 text-zinc-600 px-2 py-0.5 rounded-full border border-zinc-200">
                Cached
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-0.5">
            Grounded assessment for {document.filename}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Question Count Selector */}
          <select
            value={numQuestions}
            onChange={(e) => {
              setNumQuestions(Number(e.target.value));
            }}
            disabled={isLoading || (data !== null && !isQuizComplete && currentIndex > 0)}
            className="text-xs p-1.5 rounded-lg border border-zinc-300 bg-white text-black cursor-pointer disabled:opacity-50"
          >
            <option value={5}>5 Questions</option>
            <option value={10}>10 Questions</option>
          </select>

          <button
            onClick={() => fetchQuiz(true)}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-medium text-black bg-zinc-100 border border-zinc-300 hover:bg-zinc-200 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Generate new quiz"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>New Quiz</span>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4 py-8">
          <div className="flex items-center gap-2.5 text-xs font-semibold text-black bg-zinc-100 p-3 rounded-xl border border-zinc-300">
            <Loader2 className="w-4 h-4 animate-spin text-black" />
            <span>Generating challenging grounded MCQs with Nemotron 3 Nano...</span>
          </div>
          <div className="space-y-3">
            <div className="h-4 bg-zinc-200 rounded-md w-full animate-pulse" />
            <div className="h-4 bg-zinc-200 rounded-md w-5/6 animate-pulse" />
            <div className="h-4 bg-zinc-200 rounded-md w-4/6 animate-pulse" />
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 bg-zinc-100 border border-zinc-300 rounded-xl text-xs text-black space-y-2 mb-6">
          <div className="font-semibold flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-black" />
            <span>Failed to generate quiz</span>
          </div>
          <p>{error}</p>
          <button
            onClick={() => fetchQuiz(true)}
            className="px-3 py-1 bg-black text-white rounded-lg text-xs font-semibold hover:bg-zinc-800 cursor-pointer"
          >
            Try Again
          </button>
        </div>
      )}

      {/* 1. Active Quiz View */}
      {data && !isLoading && !isQuizComplete && currentQuestion && (
        <div className="space-y-5 animate-in fade-in duration-200">
          {/* Progress Indicator */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-zinc-600 font-medium">
              <span className="font-semibold text-black">
                Question {currentIndex + 1} of {data.questions.length}
              </span>
              <span className="bg-zinc-100 text-black border border-zinc-300 px-2 py-0.5 rounded-full text-[11px] font-semibold">
                {currentQuestion.topic}
              </span>
            </div>
            <div className="w-full bg-zinc-100 h-1.5 rounded-full overflow-hidden border border-zinc-200">
              <div
                className="bg-black h-full transition-all duration-300"
                style={{
                  width: `${((currentIndex + 1) / data.questions.length) * 100}%`,
                }}
              />
            </div>
          </div>

          {/* Question Card */}
          <div className="bg-white border border-zinc-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="text-sm md:text-base font-semibold text-black leading-snug">
              {currentQuestion.question}
            </div>

            {/* Options List - Pure Monochrome */}
            <div className="space-y-2 pt-1">
              {currentQuestion.options.map((opt, idx) => {
                const isSelected = selectedOption === opt;
                const isCorrect =
                  opt.trim().toLowerCase() ===
                  currentQuestion.correct_answer.trim().toLowerCase();

                let optionStyle =
                  "border-zinc-200 hover:border-black hover:bg-zinc-50 bg-white text-black";

                if (isAnswerSubmitted) {
                  if (isCorrect) {
                    optionStyle =
                      "border-black bg-zinc-100 text-black font-semibold";
                  } else if (isSelected && !isCorrect) {
                    optionStyle =
                      "border-zinc-400 bg-zinc-100 text-zinc-500 font-medium";
                  } else {
                    optionStyle = "border-zinc-200 bg-zinc-50 text-zinc-400";
                  }
                } else if (isSelected) {
                  optionStyle =
                    "border-black bg-zinc-100 text-black font-semibold ring-1 ring-black";
                }

                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => !isAnswerSubmitted && setSelectedOption(opt)}
                    disabled={isAnswerSubmitted}
                    className={`w-full p-3.5 rounded-xl border text-left text-xs md:text-sm transition-all flex items-center justify-between gap-3 cursor-pointer disabled:cursor-default ${optionStyle}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="w-6 h-6 rounded-lg bg-zinc-100 border border-zinc-300 flex items-center justify-center text-xs font-mono font-semibold text-black shrink-0">
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <span className="leading-relaxed">{opt}</span>
                    </div>

                    {isAnswerSubmitted && (
                      <div className="shrink-0">
                        {isCorrect ? (
                          <CheckCircle2 className="w-5 h-5 text-black" />
                        ) : isSelected ? (
                          <XCircle className="w-5 h-5 text-zinc-400" />
                        ) : null}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Answer Feedback & Explanation */}
            {isAnswerSubmitted && (
              <div
                className="p-4 rounded-xl border border-zinc-300 bg-zinc-50 text-xs space-y-1.5 animate-in fade-in duration-150"
              >
                <div className="font-bold flex items-center gap-1.5 text-black">
                  {selectedOption?.trim().toLowerCase() ===
                  currentQuestion.correct_answer.trim().toLowerCase() ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-black" />
                      <span>Correct</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-zinc-500" />
                      <span>Incorrect. Correct answer: {currentQuestion.correct_answer}</span>
                    </>
                  )}
                </div>
                <p className="leading-relaxed pl-5.5 text-zinc-700">
                  {currentQuestion.explanation}
                </p>
                {currentQuestion.page_hint && (
                  <div className="pl-5.5 text-[11px] text-zinc-500 font-mono">
                    Refer to Page {currentQuestion.page_hint} of the document.
                  </div>
                )}
              </div>
            )}

            {/* Action Bar */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100">
              {!isAnswerSubmitted ? (
                <button
                  type="button"
                  onClick={handleSubmitAnswer}
                  disabled={!selectedOption}
                  className="px-5 py-2.5 bg-black hover:bg-zinc-800 disabled:bg-zinc-200 text-white disabled:text-zinc-400 font-semibold text-xs rounded-xl transition-all cursor-pointer disabled:cursor-not-allowed shadow-xs"
                >
                  Submit Answer
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleNextQuestion}
                  className="px-5 py-2.5 bg-black hover:bg-zinc-800 text-white font-semibold text-xs rounded-xl transition-all cursor-pointer flex items-center gap-1.5 shadow-xs"
                >
                  <span>{currentIndex + 1 < data.questions.length ? "Next Question" : "See Final Score"}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 2. Quiz Complete / Score Screen */}
      {isQuizComplete && evaluation && (
        <div className="space-y-6 animate-in zoom-in-95 duration-200">
          {/* Score Header Card */}
          <div className="bg-white border border-zinc-200 rounded-2xl p-6 md:p-8 text-center shadow-xs space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-zinc-100 text-black border border-zinc-200 mx-auto flex items-center justify-center">
              <Award className="w-8 h-8" />
            </div>

            <h3 className="text-xl font-bold text-black">
              Quiz Complete!
            </h3>

            <div className="flex items-center justify-center gap-6 py-2">
              <div>
                <div className="text-3xl font-extrabold text-black">
                  {evaluation.score} / {evaluation.total}
                </div>
                <div className="text-xs text-zinc-500 font-medium">Final Score</div>
              </div>
              <div className="h-8 w-px bg-zinc-200" />
              <div>
                <div className="text-3xl font-extrabold text-black">
                  {evaluation.accuracy_percentage}%
                </div>
                <div className="text-xs text-zinc-500 font-medium">Accuracy</div>
              </div>
            </div>

            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={handleRetake}
                className="px-4 py-2 bg-black hover:bg-zinc-800 text-white text-xs font-semibold rounded-xl transition-all cursor-pointer flex items-center gap-1.5 shadow-xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Retake Quiz</span>
              </button>

              <button
                onClick={() => fetchQuiz(true)}
                className="px-4 py-2 bg-zinc-100 hover:bg-zinc-200 text-black text-xs font-semibold rounded-xl transition-all cursor-pointer border border-zinc-300"
              >
                Generate New Questions
              </button>
            </div>
          </div>

          {/* Weak Topics Analysis */}
          {evaluation.weak_topics.length > 0 && (
            <div className="bg-zinc-50 border border-zinc-300 rounded-2xl p-5 space-y-3">
              <h4 className="text-xs font-bold text-black uppercase tracking-wider flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-black" />
                Topics that may need revision:
              </h4>

              <div className="space-y-2">
                {evaluation.weak_topics.map((wt, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-white rounded-xl border border-zinc-200 flex items-center justify-between text-xs"
                  >
                    <div className="font-semibold text-black">{wt.topic}</div>
                    <div className="text-zinc-600 font-medium">
                      {wt.incorrect} of {wt.total} missed ({wt.accuracy_percentage}% accuracy)
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Question Review List */}
          {data && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                Detailed Question Review
              </h4>
              <div className="space-y-2.5">
                {data.questions.map((q) => {
                  const userAns = userAnswers.find((a) => a.question_id === q.id);
                  const isCorrect =
                    userAns &&
                    userAns.user_answer.trim().toLowerCase() ===
                      q.correct_answer.trim().toLowerCase();

                  return (
                    <div
                      key={q.id}
                      className={`p-4 rounded-xl border text-xs space-y-1.5 ${
                        isCorrect
                          ? "bg-white border-zinc-200 text-black"
                          : "bg-zinc-50 border-zinc-300 text-black"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-black">
                          {q.id}. {q.question}
                        </span>
                        {isCorrect ? (
                          <span className="text-black font-semibold flex items-center gap-1 shrink-0">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Correct
                          </span>
                        ) : (
                          <span className="text-zinc-500 font-semibold flex items-center gap-1 shrink-0">
                            <XCircle className="w-3.5 h-3.5" /> Missed
                          </span>
                        )}
                      </div>
                      <div className="text-zinc-700 pl-4 border-l-2 border-zinc-300 space-y-0.5 mt-1">
                        <div>
                          <strong>Correct:</strong> {q.correct_answer}
                        </div>
                        {!isCorrect && userAns && (
                          <div className="text-black font-semibold">
                            <strong>Your Answer:</strong> {userAns.user_answer}
                          </div>
                        )}
                        <p className="text-zinc-500 pt-1 leading-relaxed">
                          {q.explanation}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
